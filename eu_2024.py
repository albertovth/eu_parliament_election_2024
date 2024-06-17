import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.transforms import Affine2D

st.set_page_config(layout="wide")

def d_hondt(votes, seats):
    quotients = [(vote_count / i, party) for party, vote_count in votes.items() for i in range(1, seats + 1)]
    quotients.sort(reverse=True, key=lambda x: x[0])
    seat_allocation = {}
    for _, party in quotients[:seats]:
        seat_allocation[party] = seat_allocation.get(party, 0) + 1
    return seat_allocation

def sainte_lague(votes, seats):
    quotients = [(vote_count / (2 * i + 1), party) for party, vote_count in votes.items() for i in range(seats)]
    quotients.sort(reverse=True, key=lambda x: x[0])
    seat_allocation = {}
    for _, party in quotients[:seats]:
        seat_allocation[party] = seat_allocation.get(party, 0) + 1
    return seat_allocation

def modified_sainte_lague(votes, seats):
    quotients = [(vote_count / 1.4, party) for party, vote_count in votes.items()]
    for party, vote_count in votes.items():
        quotients.extend([(vote_count / (2 * i + 1), party) for i in range(1, seats)])
    quotients.sort(reverse=True, key=lambda x: x[0])
    seat_allocation = {}
    for _, party in quotients[:seats]:
        seat_allocation[party] = seat_allocation.get(party, 0) + 1
    return seat_allocation

def largest_remainder(votes, seats, quota_func):
    total_votes = sum(votes.values())
    quota = quota_func(total_votes, seats)
    allocation = {party: int(vote_count // quota) for party, vote_count in votes.items()}
    remainders = {party: vote_count % quota for party, vote_count in votes.items()}
    remaining_seats = seats - sum(allocation.values())
    sorted_remainders = sorted(remainders.items(), key=lambda x: x[1], reverse=True)
    for party, _ in sorted_remainders[:remaining_seats]:
        allocation[party] += 1
    return allocation

def hare_quota(total_votes, seats):
    return total_votes / seats

def convert_to_float(value):
    try:
        return float(value.strip('%')) / 100.0
    except ValueError:
        return 0.0

def allocate_seats(votes, method, seats, threshold, quota_func=None):
    total_votes = sum(votes.values())
    votes = {party: vote for party, vote in votes.items() if vote / total_votes >= threshold}
    if method == largest_remainder:
        return method(votes, seats, quota_func)
    else:
        return method(votes, seats)

def allocate_seats_by_constituencies(df, methods):
    results = []
    for constituency, method_params in methods.items():
        if constituency not in df['Distrikt'].unique():
            st.warning(f"Column for {constituency} not found in the data.")
            continue
        for method_name, seats, threshold, *extra in method_params:
            method = method_name
            votes = {}
            for party in df['Parti'].unique():
                filtered_df = df[(df['Distrikt'] == constituency) & (df['Parti'] == party)]
                if not filtered_df.empty:
                    votes[party] = filtered_df['Stemmer'].values[0]
            
            if not votes:
                st.warning(f"No valid votes found for {constituency}.")
                continue
            
            allocation = allocate_seats(votes, method, seats, threshold, hare_quota)
            for party, seat_count in allocation.items():
                results.append({'Parti': party, 'Constituency': constituency, 'Seats': seat_count})
    return pd.DataFrame(results)

def plot_half_circle_chart(data, colors, kategori_mapping):
    aggregated_data = data.groupby(['Political group', 'Kategori']).sum().reset_index()
    aggregated_data = aggregated_data.sort_values(by='Kategori', ascending=False)
    
    fictitious_party = pd.DataFrame({
        'Political group': ['Fiktivt Parti'],
        'Kategori': [0],
        'Seats': [sum(aggregated_data['Seats'])]
    })
    aggregated_data = pd.concat([aggregated_data, fictitious_party], ignore_index=True)
    
    total_mandates = sum(aggregated_data['Seats'])
    
    if total_mandates == 0:
        st.error("The total of seats cannot be zero.")
        return
    
    angles = aggregated_data['Seats'] / total_mandates * 360  
    
    fig, ax = plt.subplots(figsize=(10, 5), subplot_kw=dict(aspect="equal"))
    startangle = 270  
    wedges, texts = ax.pie(
        angles,
        startangle=startangle,
        colors=[colors.get(kategori, "#FFFFFF") if kategori != 0 else "#FFFFFF" for kategori in aggregated_data['Kategori']],
        wedgeprops=dict(width=0.3, edgecolor='none')
    )
    
    labels = []
    for i, wedge in enumerate(wedges):
        if aggregated_data['Political group'].iloc[i] == 'Fiktivt Parti':
            continue
        angle = (wedge.theta2 - wedge.theta1) / 2.0 + wedge.theta1
        x = np.cos(np.radians(angle))
        y = np.sin(np.radians(angle))

        label = ax.text(
            x * 0.7, y * 0.7,
            f"{aggregated_data['Political group'].iloc[i]}: {aggregated_data['Seats'].iloc[i]}",
            horizontalalignment='center',
            verticalalignment='center',
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.6),
            rotation=90
        )
        labels.append(label)
    
    plt.gca().set_aspect('equal')
    fig.tight_layout()
    plt.gca().set_position([0, 0, 1, 1])
    fig.canvas.draw()
    
    trans_data = Affine2D().rotate_deg(90) + ax.transData
    for text in texts:
        text.set_transform(trans_data)
    for wedge in wedges:
        wedge.set_transform(trans_data)
    for label in labels:
        label.set_transform(trans_data)
    
    ax.set(aspect="equal", title="Seat distribution among political groups\nin the European Parliament")
    st.pyplot(fig)

file_path = 'https://raw.githubusercontent.com/albertovth/eu_parliament_election_2024/main/default_values_eu_parliamentary_election_2024.csv'
df = pd.read_csv(file_path)

districts = [col for col in df.columns if col not in ['Parti', 'Kategori','Slider group','Party code','Political group']]
email_address = "alberto@vthoresen.no"
st.title("EU Parliament Election 2024")
st.markdown(f"Contact: [Alberto Valiente Thoresen](mailto:{email_address})")
st.markdown("""
Adjust your forecasts using the menu on the left. Voter turnout and voters by EU parliamentary constituency can also be updated at the bottom of the menu on the left.

The starting point for the simulation is the first preliminary forecast for the EU Parliament Election 2024, presented [here](https://results.elections.europa.eu/en/), with rough population estimates for 2024, provided [here](https://ec.europa.eu/eurostat/cache/metadata/en/demo_popep_esms.htm). Constituency results for Belgium were obtained from the same source.
Constituency results for Italy and Poland were obtained from [Eligendo](https://elezioni.interno.gov.it/europee/scrutini/20240609/scrutiniEI), maintained by the Ministero dell'Interno Direzione Centrale per i Servizi Elettorali, and [European Parliament Election 2024](https://wybory.gov.pl/pe2024/en/wynik/pl), maintained by Państwowa Komisja Wyborcza, respectively.
When specific vote shares by party per constituency are not available, these are estimated on the basis on the expected vote share by party for the respective member state. This approach is used for preliminary figures for Ireland and its constituencies, where reliable preliminary figures were unavailable at the time this app was published, due to the complexities inherent to the Irish electoral system.

Default voter turnout is based on results published [here](https://results.elections.europa.eu/).

Voting percentages for each party, voter turnout, and number of voters can be updated by adjusting the sliders, for more accurate and recent results.

This program calculates seat allocation by applying the appropriate method used in each constituency, considering the number of seats available and current legal party thresholds. These methods include the [D'Hondt Method](https://en.wikipedia.org/wiki/D%27Hondt_method), [Sainte-Laguë Method (including the modified version)](https://en.wikipedia.org/wiki/Sainte-Lagu%C3%AB_method), and [Largest Remainder Method](https://en.wikipedia.org/wiki/Largest_remainders_method). An overview of the methods used by constituency is presented [here](https://en.wikipedia.org/wiki/2024_European_Parliament_election).
The forecasts are more precise in the allocation of seats per party in each constituency, based on the quality of the data. However, results presented by the model at the level of political groups are merely indicative, considering that it is not possible to forecast statistically the decision of MEPs or parties on which political group to affiliate to. The model in this progrma assumes an affiliation to one political group per political party in a constituency. But as we know, this does not refleft practice. 
In the future, the model may be adapted to allow the user to distribute allocated seats by constituency to each political group.

**Note**: For simplicity, this program uses the Sainte-Laguë method instead of the [Single Transferable Vote (STV)](https://en.wikipedia.org/wiki/Single_transferable_vote) method for Ireland and Malta, which actually use the STV method in practice. The Sainte-Laguë method still provides proportional representation at the political group level. For more information on the intricacies of the STV method, see [Single Transferable Vote - Disadvantages](https://aceproject.org/main/english/es/esf04b.htm). This summary provides a good overview of the challenges involved in forecasting this method, solely based on party preference and programming such forecasts.

A diagram showing the resulting distribution of seats in the forecast is presented below. It may take some time to visualize due to the processing time for each calculation.
""")

percentage_dict = {}
participation_dict = {}
voters_dict={}
st.sidebar.header("You can adjust percentages here")
slider_groups = df['Slider group'].unique()
for slider_group in slider_groups:
    st.sidebar.subheader(slider_group)
    group_df = df[df['Slider group'] == slider_group]
    for index, row in group_df.iterrows():
        distrikt = slider_group
        if row['Parti'] != 'Valgdeltagelse' and isinstance(row[distrikt], str) and '%' in row[distrikt]:
            default_percentage = float(row[distrikt].strip('%'))
            modified_percentage = st.sidebar.slider(
                f"{row['Parti']} ({distrikt})", 0.0, 100.0, default_percentage,
                key=f"{row['Parti']}_{distrikt}_{index}"
            )
            percentage_dict[(row['Parti'], distrikt)] = f"{modified_percentage}%"
                
st.sidebar.header("You can adjust election turnout by country here")
for slider_group in slider_groups:
    st.sidebar.subheader(slider_group)
    group_df = df[df['Slider group'] == slider_group]
    for index, row in group_df.iterrows():
        distrikt = slider_group
        if row['Parti'] == 'Valgdeltagelse' and isinstance(row[distrikt], str) and '%' in row[distrikt]:
            default_participation = float(row[distrikt].strip('%'))
            modified_participation = st.sidebar.slider(f"Turnout ({distrikt})", 0.0, 100.0, default_participation)
            participation_dict[distrikt] = f"{modified_participation}%"
            
st.sidebar.header("You can adjust voters by country here")
for slider_group in slider_groups:
    st.sidebar.subheader(slider_group)
    group_df = df[df['Slider group'] == slider_group]
    for index, row in group_df.iterrows():
        distrikt = slider_group
        if row['Parti'] == 'Antall personer med stemmerett' and isinstance(row[distrikt], str):
            default_voters = float(row[distrikt])
            modified_voters = st.sidebar.slider(f"Voters ({distrikt})", 0.0, 100000000.0, default_voters)
            voters_dict[distrikt] = f"{modified_voters}"

def calculate_stemmer(row, percentage_dict, participation_dict):
    stemmer_data = []
    for distrikt in districts:
        percentage = percentage_dict.get((row['Parti'], distrikt), row[distrikt])
        valgdeltakelse = participation_dict.get(distrikt, df[df['Parti'] == 'Valgdeltagelse'][distrikt].values[0])
        personer_med_stemmerett = voters_dict.get(distrikt, df[df['Parti'] == 'Antall personer med stemmerett'][distrikt].values[0])
       
        if pd.notna(percentage) and pd.notna(valgdeltakelse) and pd.notna(personer_med_stemmerett):
            percentage_value = float(percentage.strip('%')) / 100
            valgdeltakelse_value = float(valgdeltakelse.strip('%')) / 100
            personer_value = float(personer_med_stemmerett)
            stemmer = percentage_value * valgdeltakelse_value * personer_value
            stemmer_data.append(stemmer)
        else:
            stemmer_data.append(np.nan)
    return stemmer_data

results = {'Parti': [], 'Distrikt': [], 'Stemmer': [], 'Kategori': []}
for index, row in df.iterrows():
    if row['Parti'] not in ['Valgdeltagelse', 'Antall personer med stemmerett']:
        stemmer_data = calculate_stemmer(row, percentage_dict, participation_dict)
        for distrikt, stemmer in zip(districts, stemmer_data):
            results['Parti'].append(row['Parti'])
            results['Distrikt'].append(distrikt)
            results['Stemmer'].append(stemmer)
            results['Kategori'].append(row['Kategori'])

results_df = pd.DataFrame(results)

results_df_english = results_df.copy()
results_df_english.columns = ['Party' if col == 'Parti' else 
                              'Constituency' if col == 'Distrikt' else 
                              'Votes' if col == 'Stemmer' else 
                              col for col in results_df_english.columns]
if 'Kategori' in results_df_english.columns:
    results_df_english.drop('Kategori', axis=1, inplace=True)

st.write("### Total votes by party and constituency")
st.dataframe(results_df_english)

country_methods = {
    'Austria': [(d_hondt, 20, 0.04)],
    'Belgium_Flemish': [(d_hondt, 13, 0.05)],
    'Belgium_French': [(d_hondt, 8, 0.05)],
    'Belgium_German': [(d_hondt, 1, 0.05)],
    'Bulgaria': [(largest_remainder, 17, 0.059, hare_quota)],
    'Croatia': [(d_hondt, 12, 0.05)],
    'Cyprus': [(largest_remainder, 6, 0.018, hare_quota)],
    'Czech Republic': [(d_hondt, 21, 0.05)],
    'Denmark': [(d_hondt, 15, 0)],
    'Estonia': [(d_hondt, 7, 0)],
    'Finland': [(d_hondt, 15, 0)],
    'France': [(d_hondt, 81, 0.05)],
    'Germany': [(sainte_lague, 96, 0)],
    'Greece': [(largest_remainder, 21, 0.03, hare_quota)],
    'Hungary': [(d_hondt, 21, 0.05)],
    'Ireland_Dublin': [(sainte_lague, 4, 0)], ## Using Sainte-Laguë instead of Single Transferable Vote for simplicity
    'Ireland_Midland_North_West': [(sainte_lague, 4, 0)],## Using Sainte-Laguë instead of Single Transferable Vote for simplicity
    'Ireland_South': [(sainte_lague, 6, 0)], ## Using Sainte-Laguë instead of Single Transferable Vote for simplicity
    'Italy_North_West': [(largest_remainder, 21, 0.04, hare_quota)],
    'Italy_North_East': [(largest_remainder, 15, 0.04, hare_quota)],
    'Italy_Central': [(largest_remainder, 14, 0.04, hare_quota)],
    'Italy_Southern': [(largest_remainder, 18, 0.04, hare_quota)],
    'Italy_Islands': [(largest_remainder, 8, 0.04, hare_quota)],
    'Latvia': [(sainte_lague, 9, 0.05)],
    'Lithuania': [(largest_remainder, 11, 0.05, hare_quota)],
    'Luxembourg': [(d_hondt, 6, 0)],
    'Malta': [(sainte_lague, 6, 0)],## Using Sainte-Laguë instead of Single Transferable Vote for simplicity
    'Netherlands': [(d_hondt, 31, 0.032)],
    'Poland_Greater_Poland': [(d_hondt, 4, 0.05)],
    'Poland_Kuyavian_Pomeranian': [(d_hondt, 2, 0.05)],
    'Poland_Lesser_Poland_Swietokrzyskie': [(d_hondt, 4, 0.05)],
    'Poland_Lodz': [(d_hondt, 3, 0.05)],
    'Poland_Lower_Silesian_Opole': [(d_hondt, 4, 0.05)],
    'Poland_Lublin': [(d_hondt, 4, 0.05)],
    'Poland_Lubusz_West_Pomeranian': [(d_hondt, 4, 0.05)],
    'Poland_Masovian': [(d_hondt, 4, 0.05)],
    'Poland_Podlaskie_Warmian_Masurian': [(d_hondt, 3, 0.05)],
    'Poland_Pomeranian': [(d_hondt, 3, 0.05)],
    'Poland_Silesian': [(d_hondt, 8, 0.05)],
    'Poland_Subcarpathian': [(d_hondt, 3, 0.05)],
    'Poland_Warsaw': [(d_hondt, 7, 0.05)],
    'Portugal': [(d_hondt, 21, 0)],
    'Romania': [(d_hondt, 33, 0.05)],
    'Slovakia': [(largest_remainder, 15, 0.05, hare_quota)],
    'Slovenia': [(d_hondt, 9, 0)],
    'Spain': [(d_hondt, 61, 0)],
    'Sweden': [(modified_sainte_lague, 21, 0.04)],
}

kategori_mapping = {
    'EPP': 8,
    'S&D': 3,
    'ECR': 9,
    'RE': 6,
    'GUE/NGL': 1,
    'G/EFA': 5,
    'ID': 10,
    'NI': 11,
    'Others': 12
}

results_allocation = allocate_seats_by_constituencies(results_df, country_methods)

results_allocation = pd.merge(results_allocation, df[['Parti', 'Political group']].drop_duplicates(), on='Parti', how='left')

results_allocation = results_allocation.drop_duplicates(subset=['Parti', 'Constituency'], keep='first')

st.write("### Seat allocation by party and constituency before projected aggregation by political group")
st.dataframe(results_allocation[['Parti', 'Constituency', 'Seats']])

results_allocation['Political group'] = results_allocation['Political group'].replace('Other parties', 'Others')

seats_by_constituency = results_allocation.groupby('Constituency')['Seats'].sum().reset_index()
st.write("### Total seats allocated by constituency")
st.dataframe(seats_by_constituency)

aggregated_results = results_allocation.groupby(['Political group']).agg({'Seats': 'sum'}).reset_index()

aggregated_results['Kategori'] = aggregated_results['Political group'].map(kategori_mapping)

st.write("### Projected Seat distribution by political group")
st.dataframe(aggregated_results)

total_seats_allocated = aggregated_results['Seats'].sum()
st.write(f"Total seats allocated: {total_seats_allocated}")

color_mapping = {
    1: '#8B0000',  
    2: '#FF0000',   
    3: '#FF6347',   
    4: '#FF7F7F',   
    5: '#006400',   
    6: '#ADD8E6',   
    7: '#0000FF',   
    8: '#00008B',   
    9: '#140080',   
    10: '#14145A',  
    11: '#FFFF00',
    12: '#999999'
}

plot_half_circle_chart(aggregated_results, color_mapping, kategori_mapping)
