from flask import Flask, render_template, request, redirect
import altair as alt
import dill
from datetime import datetime,timedelta
import pandas as pd
import json

app = Flask(__name__)

def prepare_news_df(ticker,startdate,enddate):   
    news = dill.load(open('data/News/'+ticker+'.pkd', 'rb'))
    #yvalues=[]
    #for date,n in news.groupby('date').agg({'count'}).to_records():
    #    for i in range(n):
    #        yvalues.append(i+1)
    #news['yvalues']=yvalues
    #news=news.reset_index()
    #news['date']=news['date'].apply(str).apply(lambda x:datetime.strptime(x[:10],'%Y-%m-%d'))
    news=news[(news.date>=startdate) & (news.date<=enddate)]
    return news

app.df_dates = dill.load(open('data/df_dates.pkd', 'rb'))
app.name_tickers = dill.load(open('data/name_tickers.pkd', 'rb'))

def create_study_dates_df(ticker,startdate,enddate):    
    ticker_dates=app.df_dates[app.df_dates.source==app.name_tickers[ticker]]
    ticker_dates.set_index('nct_id',inplace=True)
    df_sdates=pd.DataFrame(columns=['date','nct_id','datetype'])
    for col in ticker_dates.iloc[:,:-2].iteritems():
        df=pd.DataFrame()
        df['date']=col[1].values
        df['nct_id']=col[1].index
        df['datetype']=col[0]
        df_sdates=df_sdates.append(df)
    df_sdates=df_sdates.dropna().sort_values('date').set_index('date')
    yvalues=[]
    for date,n in df_sdates.groupby('date').agg({'count'})[[('nct_id','count')]].to_records():
        for i in range(n):
            yvalues.append(i+1)
    df_sdates['yvalues']=yvalues
    df_sdates=df_sdates.reset_index()
    df_sdates['date']=df_sdates['date'].apply(str).apply(lambda x:datetime.strptime(x,'%Y-%m-%d'))
    df_sdates=df_sdates[(df_sdates.date>=startdate) & (df_sdates.date<=enddate)]
    titles=[]
    for nct_id in df_sdates.nct_id:
        titles.append(ticker_dates.brief_title[nct_id])
    df_sdates['title']=titles
    return df_sdates

ticker_first_dates=dill.load(open('data/ticker_first_dates.pkd', 'rb'))

def plotChart(ticker,startdate,enddate):
    
    if startdate<ticker_first_dates[ticker]:
        startdate=ticker_first_dates[ticker]
        enddate=startdate+timedelta(days=100)
        
    if startdate>app.currdate:
        startdate=app.currdate-timedelta(days=100)
        enddate=app.currdate
        
    source = dill.load(open(
        'data/EOD/'+ticker+'.pkd', 'rb')).loc[startdate:enddate,'adjClose':'adjOpen'].reset_index()
        
    source.rename(columns={
        'adjOpen':'Open','adjHigh':'High','adjLow':'Low','adjClose':'Close'},inplace=True)
    source['prevClose']=source.Close.shift(1)
    
    pos_neg_color = alt.condition("datum.Close >= datum.prevClose",
                                     alt.value("green"),
                                     alt.value("red"))
    chart_title='{}: {} From:{} to {}'.format(
        ticker,app.name_tickers[ticker],str(startdate)[:10],str(enddate)[:10])
    
    base = alt.Chart(source,width=800,height=600,title=chart_title).encode(
        alt.X('date',axis=alt.Axis(format='%m/%d', title='Date')
        ),color=pos_neg_color,tooltip=['date','Open','High','Low','Close'])

    range_ = base.mark_rule(cursor='crosshair').encode(
        alt.Y('Low',title='Price',scale=alt.Scale(zero=False)),
        alt.Y2('High'))
    open_ = base.mark_point(shape='stroke', xOffset=-1).encode(alt.Y('Open:Q'))
    close_= base.mark_point(shape='stroke', xOffset= 1).encode(alt.Y('Close:Q'))

    df_studies=create_study_dates_df(ticker,startdate,enddate)
    
    plot_studies=False
    llow=min(source.Low)
    if len(df_studies)>0:
        plot_studies=True 
        step=(max(source.High)-llow)/max(df_studies.yvalues)
    
        df_studies['adjYvalues']=llow+df_studies.yvalues*step
        df_studies['title']=df_studies.title#.apply(lambda x:x[:80])

        sdates=alt.Chart(df_studies).mark_circle(size=100,cursor='crosshair',filled=True).encode(
            x='date',y='adjYvalues',tooltip=['datetype','date','nct_id','title'],color='nct_id')
        
    newsdata = prepare_news_df(ticker,startdate,enddate)
    newsdata['adjYvalues']=llow-newsdata.yvalues*(max(source.High)-llow)/20

    news_dates=alt.Chart(newsdata).mark_circle(
        size=100,cursor='crosshair',filled=True,color='green').encode(
        x='date',y='adjYvalues',tooltip=['date','text'])

    if plot_studies:
        return alt.layer(range_,open_,close_,sdates,news_dates)
    else:
        return alt.layer(range_,open_,close_,news_dates)

app.ticker='ABBV'
app.currdate=datetime.now()
app.enddate=app.currdate
app.deltaback=timedelta(days=100)
app.deltafwd=timedelta(days=0)

@app.route('/', methods=['POST', 'GET'])
def index():

    app.ticker=request.form.get('ticker',app.ticker)
    
    back=int(request.form.get('deltaback',0))
    app.deltaback=app.deltaback+timedelta(days=back)
    fwd=int(request.form.get('deltafwd',0))
    app.deltafwd=timedelta(days=fwd)
    
    goto_start=request.form.get('start','')
    goto_end=request.form.get('end','')
    
    if fwd>0 and app.deltaback>timedelta(days=100):
        app.deltaback=app.deltaback-app.deltafwd
    
    if goto_start:
        startdate=ticker_first_dates[app.ticker]
        app.deltaback=app.enddate-startdate
    if goto_end:
        app.deltaback=timedelta(days=100)
        
    startdate=app.enddate-app.deltaback
    
    chart = plotChart(app.ticker,startdate,startdate+timedelta(days=100))
    
    return render_template('index.html',chart=chart.to_json())

if __name__ == '__main__':

    app.run(port=33507,debug=True)

