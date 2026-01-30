import folium, json, os

COLLECT_JSON = "collect_points.json"
MAP_HTML = "map_test.html"
# param: none
# incearca sa incarce punctele din JSON; daca nu merge, continua cu lista goala

try:
    with open(COLLECT_JSON, "r", encoding="utf-8") as f:
        points = json.load(f)
except Exception as e:
    print(" Nu pot citi JSON:", e)
    points = []

print(f"Puncte încărcate: {len(points)}")
# param: none
# creeaza harta centrata pe Timisoara (OpenStreetMap)

m = folium.Map(location=[45.75, 21.23], zoom_start=13, tiles="OpenStreetMap")
# param: p (dict) din points
# pune markere pe harta + popup cu link spre Google Maps
for p in points:
    gmaps_url = f"https://www.google.com/maps?q={p['lat']},{p['lon']}"
    html = (
        f"<b>{p.get('name','')}</b><br/>{', '.join(p['types'])}"
        f"<br/><a href='{gmaps_url}' target='_blank'> Deschide în Google Maps</a>"
    )
    folium.Marker([p["lat"], p["lon"]],
                  popup=folium.Popup(html, max_width=280),
                  tooltip=p.get("name", ""),
                  icon=folium.Icon(color="green", icon="recycle", prefix="fa")).add_to(m)
# params: none
# ce face: salveaza harta in map_test.html si afiseaza calea absoluta
m.save(MAP_HTML)
print(f" Harta salvată: {MAP_HTML} ({os.path.abspath(MAP_HTML)})")
