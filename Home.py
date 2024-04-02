import streamlit as st
from datetime import date
import pandas as pd
from openai import OpenAI
import datetime
import plotly.express as px
from cfpb_api_client import CFPBApiClient

# Load environment variables
from dotenv import load_dotenv
import os
load_dotenv()


# Constant
COMPLAINT_SUMMARIZATION_PROMPT = """\
The user will present a table of customer complaints. Your task is to use it to:
1. Look for commonalities in the complaints. Are there specific products or services that are generating more complaints? Are complaints more frequent during certain times?
2. Delve into the details of a few individual complaints that stand out to understand the specifics of customer grievances and their expectations.
Note that some of the contents may be redacted for privacy reasons with [R] in the text."""

DEFAULT_SUMMARY ="""\
### Common Complaint Themes

1. **Product Issues**: The majority of complaints revolve around checking or savings accounts, followed by credit card services. There are also mentions of credit reporting or other personal consumer reports, and money transfer, virtual currency, or money service. This indicates that the primary areas of customer dissatisfaction are related to banking accounts and credit services.

2. **Recurring Issues**:
   - **Overdraft Fees**: Several complaints about checking or savings accounts mention high overdraft fees, such as being charged $34.00 for an overdraft of $7.00. This suggests a systemic issue with how overdrafts are handled and communicated to customers.
   - **Account Access and Transaction Issues**: Customers have encountered problems accessing their funds, closing their accounts, and issues with transactions getting stuck due to system glitches or account holds.
   - **Disputes with Credit Card Transactions**: Complaints about credit cards often mention disputes over fraudulent charges and issues with the bank’s dispute resolution process.

3. **Timing**: A significant number of complaints are concentrated around the end of January 2024, with a particular emphasis on the last day of the month. This may indicate systemic issues or process breakdowns during this time frame, possibly related to end-of-month financial activities.

### Detailed Examination of Individual Complaints

1. **Overdraft Fees Complained by Customer ID 8256566**:
   - **Issue**: The customer is upset about multiple high overdraft fees for relatively small amounts.
   - **Expectation**: It appears the customer expects lower or waived overdraft fees, especially since they mention having pending credits to their account that would cover the overdrafts.

2. **Account Closure Issue Complained by Customer ID 8261625**:
   - **Issue**: The customer mentions an inability to close their savings account due to a system issue, followed by a claim of a wrongful balance shown upon account closure.
   - **Expectation**: There's an evident expectation for a smoother account closure process and accurate final account balance communication.

3. **Credit Card Fraud Issue Complained by Customer ID 8258217**:
   - **Issue**: The customer faced fraudulent charges on their account and struggled with the bank’s process to remove those charges.
   - **Expectation**: The customer likely expected a more straightforward process for resolving fraud charges, including clarity on account closure and reconciliation.

4. **Money Transfer Complaint ID 8258585**:
   - **Issue**: A customer sends a large sum to a fraudulent account due to intercepted wire instructions and struggles with getting assistance from the bank.
   - **Expectation**: The customer seeks effective communication regarding the status of their funds and expects the bank to assist in recovering the lost money.

### Conclusion
The complaints suggest that JPMORGAN CHASE & CO. could improve in areas related to handling overdraft fees, system glitches affecting account transactions and closures, clarity and efficiency in dispute resolutions, and support for fraud and scam victims. Addressing these issues could potentially reduce the volume of similar complaints and improve overall customer satisfaction."""

LLM_MODEL_OPTIONS = ["gpt-3.5-turbo-0125", "gpt-3.5-turbo"]

#############
#   SETUP   #
#############
# Page Configuration
st.set_page_config(
    page_title="Customer Complaints",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)
# initialize session state
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = pd.read_csv('complaints.csv')
if 'trend' not in st.session_state:
    st.session_state['trend'] = pd.read_csv('trend.csv')
if 'client' not in st.session_state:
    st.session_state['client'] = CFPBApiClient()
if 'generated' not in st.session_state:
    # search resets generated -> False
    # generate sets generated -> True
    st.session_state['generated'] = True
if 'summary' not in st.session_state:
    st.session_state['summary'] = DEFAULT_SUMMARY


def cleanup_narratives(series: pd.Series) -> pd.Series:
    # Define regex pattern to replace Xs with [redacted]
    pattern = r'\bX+(?:[^a-zA-Z\d]X+)*'
    replacement = '[R]'
    # Use vectorized substitution
    return series.str.replace(pattern, replacement, regex=True)


def fetch_data(client: CFPBApiClient, **kwargs) -> pd.DataFrame:
    """
    Fetch data from the CFPB API and return it as a DataFrame with cleaned narratives and capped length (500 chars).
    """
    # Fetch data from the CFPB API
    search_results = client.search_complaints(
        field="all",
        sort="created_date_desc",
        **kwargs
    )
    # Save the search results as a df in session state
    df_result = pd.DataFrame([hit['_source'] for hit in search_results['hits']['hits']])
    # Make sure that the df has the column 'complaint_what_happened' (not empty)
    if 'complaint_what_happened' in df_result.columns:
        # Convert the date_received and date_sent_to_company columns to datetime
        df_result['date_received'] = pd.to_datetime(df_result['date_received'])
        df_result['date_sent_to_company'] = pd.to_datetime(df_result['date_sent_to_company'])
        # Sort the df
        df_result.sort_values(by=['company', 'date_received', 'product', 'complaint_id'], inplace=True)
        # Clean up redacted text
        df_result['clean_narratives'] = cleanup_narratives(df_result['complaint_what_happened'])
        # Limit the length of the narratives to 500 characters
        df_result['clean_narratives'] = df_result['clean_narratives'].str.slice(0, 500)
    
    # Fetch trend for the same search
    trend = client.get_trend(
        field="all",
        trend_interval="month",
        lens='product',
        sub_lens='sub_product',
        **kwargs,
    )
    data = []
    # Collect trend data for each product
    for item in trend['aggregations']['product']['product']['buckets']:
        df_item = pd.DataFrame(item["trend_period"]['buckets'])[['key_as_string', 'doc_count']]
        df_item.rename(columns={'key_as_string': 'Date', 'doc_count': item['key']}, inplace=True)
        df_item.set_index('Date', inplace=True)
        data.append(df_item)
    df_trend = pd.concat(data, axis=1).reset_index()
    # Convert the date column to datetime
    df_trend['Date'] = pd.to_datetime(df_trend['Date'])
    # Update the session state
    st.session_state['trend'] = df_trend.fillna(0)

    # Update the session state
    st.session_state['generated'] = False

    return df_result


def summarize(api_key: str, model: str, df_in: pd.DataFrame) -> str:
    # Preprocess df
    # Sort the df
    df_in = df_in.sort_values(by=['company', 'date_received', 'product'])
    # Set the index to reduce duplicated data in the prompt to reduce token usage
    df_in = df_in.set_index(['company', 'date_received', 'product', 'complaint_id'])[['clean_narratives']]

    # Use Gen AI to summarize the complaints
    client = OpenAI(
        api_key=api_key,
        base_url='https://oai.hconeai.com/v1',
        default_headers={ # Helicone monitoring layer
            "Helicone-Auth": f"Bearer {os.getenv('HELICONE_API_KEY')}"
        },
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": COMPLAINT_SUMMARIZATION_PROMPT},
            {"role": "user", "content": df_in.to_html()[:20_000]}, # Cap at 20k characters
        ],
    )
    
    # Update the session state
    st.session_state['generated'] = True

    return response.choices[0].message.content


##############
#  SIDE BAR  #
##############
# CFPB Query Parameters
st.sidebar.header("CFPB Complaint Search Input")
companies = st.sidebar.multiselect("Select Company", default=CFPBApiClient.COMPANY_NAMES[0], options=CFPBApiClient.COMPANY_NAMES, placeholder="Select a company", key=None)
# Number of search results to display
size = st.sidebar.slider("Number of Results", min_value=5, max_value=100, value=20, step=1, format="%d", key=None)
# Select the time interval for data retrieval
start_date = st.sidebar.date_input("Start Date", value=datetime.date(2023, 1, 1), min_value=None, max_value=date.today(), format="MM/DD/YYYY", key=None)
end_date = st.sidebar.date_input("End Date", value=max(datetime.date(2023, 12, 31), start_date), min_value=start_date, max_value=date.today(), format="MM/DD/YYYY", key=None)
# Selection Criteria
has_narrative = st.sidebar.checkbox("Has Narrative", value=True, key=None)

# Create a button to fetch data
if st.sidebar.button("Fetch Data"):
    with st.spinner("Fetching Data..."):
        client : CFPBApiClient = st.session_state['client']
        # Save the search results in session state
        st.session_state['search_results'] = fetch_data(
            client=client,
            company=companies,
            size=size,
            date_received_min=start_date.strftime("%Y-%m-%d") if start_date else None,
            date_received_max=end_date.strftime("%Y-%m-%d") if end_date else None,
            has_narrative="true" if has_narrative else "false",
        )

# Once data is fetched, allow Gen AI function
st.sidebar.header("Summarization")
# GenAI API Configuration
st.sidebar.header("Gen AI Configuration")
# Select Model
model = st.sidebar.selectbox("Select Model", options=LLM_MODEL_OPTIONS, key=None)
# Create a button to generate text
result: pd.DataFrame | None = st.session_state['search_results']
# Disable the button if there are no search results or if the API key or model is empty
disable_generate = (result is None) | (result.empty) | (model not in LLM_MODEL_OPTIONS)
if st.sidebar.button("Generate Summary", disabled=disable_generate):
    with st.sidebar.status("Generating Summary..."):
        st.session_state['summary'] = summarize(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=model,
            df_in=result
        )


#############
# MAIN PAGE #
#############
st.title("Gen AI for Handling Customer Complaints")
st.write("""\
This demo showcases the application of Generative AI (Gen AI) in managing customer complaints,
- The example complaint data is live from the Consumer Financial Protection Bureau (CFPB).
- With the example data, Gen AI can then be used to summarize the complaints and provide specific insights into the data. (In its
    current state, the demo only supports OpenAI API, but it is fairly easy to extend it to other APIs.)

To reduce cost, the data is preprocessed to minimize the amount of tokens sent to the model. The more results you fetch, the more
cost you will incur. So be mindful when choosing the number of results. We also recommend using monitoring tools to keep track of
token usage and leverage optimizations techniques like caching.

While not shown in this demo, we have also experimented with using Gen AI for other tasks like:
1. Simplifying feedback collection and self-triage for customer support
2. Generating starter responses to customer complaints which unlocks efficiency gain
3. Automatic visualization of data using natural language which democratizes data analysis for non-technical users and stakeholders

While some of these applications might not be relevant using the data shown here, the similar techniques can be applied to other 
unstructured or private data, to modernize data collection and streamline customer support and data analysis workflows.  We hope
you find this demo helpful and inspiring for your own projects.\
""")

# Display the search results if there are any
if st.session_state['search_results'] is not None:
    st.header("Search Results")
    # Display a dataframe of the search results
    df: pd.DataFrame = st.session_state['search_results']
    # Check if the dataframe is empty
    if df.empty:
        st.warning("No results found.")
    else:
        # Plot a line chart of the number of complaints over time by company
        st.subheader("Trends")
        # Plot the data
        fig = px.line(
            data_frame=st.session_state['trend'].set_index('Date'),
            title='Complaints Over Time',
            labels={'value': 'Number of Complaints', 'variable': 'Product'},
        )
        st.plotly_chart(fig, use_container_width=True)

        # Display the dataframe
        st.subheader("Complaints Table")
        st.dataframe(
            data=df,
            hide_index=True,
            column_order=['company', 'date_received', 'product', 'complaint_what_happened'],
            column_config={
                "date_received": st.column_config.DatetimeColumn(
                        label='Date',
                        format="MM/DD/YYYY",
                    ),
                "complaint_what_happened": st.column_config.TextColumn(
                    label='Narrative',
                ),
                "company": "Company",
                "product": "Product"
            }
        )

# Display the generated summary if available
if st.session_state['generated']:
    st.header("Generated Summary")
    st.info(st.session_state['summary'].replace('$', '\$'))