
import pprint

from files.classes.volunteer_janitor import VolunteerJanitorRecord

from files.__main__ import app, db_session

@app.cli.command('volunteer_janitor_histogram')
def volunteer_janitor_histogram_cmd():
    import pandas as pd
    import matplotlib.pyplot as plt

    result_set = db_session().query(VolunteerJanitorRecord.recorded_utc).all()

    # convert the result into a pandas DataFrame
    df = pd.DataFrame(result_set, columns=['recorded_utc'])

    # convert the date column to datetime
    df['recorded_utc'] = pd.to_datetime(df['recorded_utc'])

    # set 'recorded_utc' as the index of the DataFrame
    df.set_index('recorded_utc', inplace=True)

    # resample the data to daily frequency
    df_resampled = df.resample('D').size()

    # plot the resampled DataFrame
    df_resampled.plot(kind='line')
    plt.title('Density of Dates over Time')
    plt.xlabel('Date')
    plt.ylabel('Count')
    
    # save the figure in SVG format
    plt.savefig('output.svg', format='svg')
    print(len(result_set))
