from flask import Flask, request, render_template, jsonify
from pymongo import MongoClient
import pandas as pd
from folium import Map, Marker, PolyLine, Icon, Tooltip

app = Flask(__name__)

# Conexiune MongoDB
client = MongoClient("mongodb+srv://calindanmarinescu:Federer1@cluster0.o1mqr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client['gps_data']
collection = db['locations']

@app.route('/')
def index():
    # Obținem lista utilizatorilor disponibili din baza de date
    users = collection.distinct('id')
    return render_template('index.html', users=users)

@app.route('/generate-route', methods=['POST'])
def generate_route():
    user_id = request.form['user']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    date_filter = request.form['date']

    # Filtrăm datele din MongoDB
    query = {
        "id": int(user_id),
        "timestamp": {"$regex": f"^{date_filter}"},
    }
    data = pd.DataFrame(list(collection.find(query)))

    if data.empty:
        return jsonify({"status": "error", "message": "Nu există date pentru criteriile selectate."})

    # Filtrare suplimentară pe interval orar
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data = data[(data['timestamp'].dt.time >= pd.to_datetime(start_time).time()) &
                (data['timestamp'].dt.time <= pd.to_datetime(end_time).time())]

    if data.empty:
        return jsonify({"status": "error", "message": "Nu există date în intervalul selectat."})

    # Creăm harta
    first_point = data.iloc[0]
    last_point = data.iloc[-1]
    m = Map(location=[float(first_point['latitude']), float(first_point['longitude'])], zoom_start=12)
    coords = [(float(row['latitude']), float(row['longitude'])) for _, row in data.iterrows()]

    # Adăugăm marcator pentru punctul de start
    start_tooltip = f"""
    <b>Utilizator:</b> {first_point['id']}<br>
    <b>Ora:</b> {first_point['timestamp']}<br>
    <b>Latitudine:</b> {first_point['latitude']}<br>
    <b>Longitudine:</b> {first_point['longitude']}
    """
    Marker(
        location=[float(first_point['latitude']), float(first_point['longitude'])],
        popup="Start",
        tooltip=Tooltip(start_tooltip),
        icon=Icon(color="green")
    ).add_to(m)

    # Adăugăm marcatoare intermediare cu tooltip-uri
    for _, row in data.iloc[1:-1].iterrows():  # Exclude primul și ultimul punct
        tooltip_text = f"""
        <b>Utilizator:</b> {row['id']}<br>
        <b>Ora:</b> {row['timestamp']}<br>
        <b>Latitudine:</b> {row['latitude']}<br>
        <b>Longitudine:</b> {row['longitude']}
        """
        Marker(
            location=[float(row['latitude']), float(row['longitude'])],
            tooltip=Tooltip(tooltip_text)
        ).add_to(m)

    # Adăugăm marcator pentru punctul de finish
    finish_tooltip = f"""
    <b>Utilizator:</b> {last_point['id']}<br>
    <b>Ora:</b> {last_point['timestamp']}<br>
    <b>Latitudine:</b> {last_point['latitude']}<br>
    <b>Longitudine:</b> {last_point['longitude']}
    """
    Marker(
        location=[float(last_point['latitude']), float(last_point['longitude'])],
        popup="Finish",
        tooltip=Tooltip(finish_tooltip),
        icon=Icon(color="red")
    ).add_to(m)

    # Adăugăm linia traseului
    PolyLine(coords, color="blue", weight=2).add_to(m)

    # Salvăm harta
    map_url = '/static/generated_route.html'
    m.save('static/generated_route.html')

    # Returnăm URL-ul către hartă
    return jsonify({"status": "success", "map_url": map_url})

if __name__ == '__main__':
    app.run(debug=True)
