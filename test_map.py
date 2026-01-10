import folium, json, os

COLLECT_JSON = "collect_points.json"
MAP_HTML = "map_test.html"

try:
    with open(COLLECT_JSON, "r", encoding="utf-8") as f:
        points = json.load(f)
except Exception as e:
    print(" Nu pot citi JSON:", e)
    points = []

print(f"Puncte încărcate: {len(points)}")

m = folium.Map(location=[45.75, 21.23], zoom_start=13, tiles="OpenStreetMap")

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

m.save(MAP_HTML)
print(f" Harta salvată: {MAP_HTML} ({os.path.abspath(MAP_HTML)})")
