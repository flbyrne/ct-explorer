from retrying import retry
import requests

tiingo_key='860a090ec307759a83ec7fa8659417327c5be8aa'

@retry(wait_fixed=2000,stop_max_attempt_number=10)
def get_response(path):

    response=requests.get(path)
    if response.ok:
        return response
    else:
        raise NameError
        
def get_EOD_data(symbol,sdate,edate):
    
    base_url='https://api.tiingo.com/tiingo/daily/'+symbol+'/prices?'
    api_key=tiingo_key#'9fa4df1e30e2fb224f1a625b7c43867b1880d05f'
    parameters={
        'token':api_key,
        'startDate':sdate,
        'endDate': edate,
    }
    response = requests.get(base_url, params=parameters)
    return response