# ═══════════════════════════════════════════════
#  map_server.py  —  Локален HTTP сървър + Leaflet карта
# ═══════════════════════════════════════════════

import http.server
import threading
import socket
import json

# ── Callback, зададен от приложението ──
_map_callback = None


def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]


MAP_PORT = _find_free_port()


class _MapHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # потиши конзолата

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length)
        try:
            data = json.loads(body)
            if _map_callback:
                _map_callback(data)
        except Exception:
            pass
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'ok')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def start_map_server():
    """Стартира HTTP сървъра в daemon нишка."""
    srv = http.server.HTTPServer(('127.0.0.1', MAP_PORT), _MapHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()


def set_map_callback(cb):
    """Задава callback функцията, извиквана при потвърждение от картата."""
    global _map_callback
    _map_callback = cb


def build_map_html(start_coords=None, end_coords=None,
                   start_name="", end_name="", road_geom=None) -> str:
    """
    Генерира self-contained Leaflet HTML карта.
    - Кликни веднъж  → Начален маркер (зелен)
    - Кликни два пъти → Краен маркер (червен) + реален маршрут OSRM
    - Бутон 'Потвърди' изпраща координатите обратно към Python
    """
    start_js = "null"
    end_js   = "null"
    road_js  = "null"
    if start_coords:
        start_js = f'[{start_coords[0]}, {start_coords[1]}]'
    if end_coords:
        end_js = f'[{end_coords[0]}, {end_coords[1]}]'
    if road_geom:
        road_js = json.dumps(road_geom)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>ЕкоСледа Карта</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#050d05; font-family:Helvetica,sans-serif; }}
  #map {{ width:100%; height:calc(100vh - 64px); }}
  #panel {{
    height:64px; background:#0a1a0a; display:flex;
    align-items:center; padding:0 16px; gap:10px;
    border-top:2px solid #22c55e;
  }}
  .info {{ color:#6b9b6b; font-size:11px; flex:1; line-height:1.6; }}
  .info b  {{ color:#4ade80; }}
  .info em {{ color:#fbbf24; font-style:normal; }}
  button {{
    background:#22c55e; color:#050d05; border:none;
    padding:8px 16px; border-radius:4px; cursor:pointer;
    font-weight:bold; font-size:12px; white-space:nowrap;
  }}
  button:hover {{ background:#39ff14; }}
  button.sec {{ background:#152b16; color:#e8ffe8; border:1px solid #2d4a2d; }}
  button.sec:hover {{ background:#0f2310; }}
  #toast {{
    position:absolute; top:10px; left:50%; transform:translateX(-50%);
    background:rgba(10,26,10,0.95); color:#4ade80;
    padding:7px 20px; border-radius:20px; font-size:12px;
    pointer-events:none; z-index:1000; border:1px solid #22c55e;
    transition: opacity 0.4s;
  }}
  #spinner {{
    display:none; position:absolute; top:10px; right:16px;
    background:rgba(10,26,10,0.92); color:#fbbf24;
    padding:6px 14px; border-radius:14px; font-size:11px; z-index:1001;
  }}
</style>
</head>
<body>
<div id="toast">🟢 Кликни за начална точка</div>
<div id="spinner">⏳ Търся маршрут…</div>
<div id="map"></div>
<div id="panel">
  <div class="info">
    🟢 <b id="sTxt">—</b> &nbsp;→&nbsp; 🔴 <b id="eTxt">—</b><br>
    🛣️ Разстояние: <b id="distTxt">—</b> &nbsp;|&nbsp;
    ⏱️ Прибл. <b id="durTxt">—</b> &nbsp;|&nbsp; <em id="routeType">—</em>
  </div>
  <button class="sec" onclick="clearAll()">✕ Изчисти</button>
  <button onclick="sendRoute()">✔ Потвърди маршрута</button>
</div>
<script>
var map = L.map('map').setView([42.7, 25.4], 7);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  attribution: '© OpenStreetMap', maxZoom:19
}}).addTo(map);

var greenIcon = new L.Icon({{
  iconUrl:'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
  shadowUrl:'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize:[25,41],iconAnchor:[12,41],popupAnchor:[1,-34],shadowSize:[41,41]
}});
var redIcon = new L.Icon({{
  iconUrl:'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
  shadowUrl:'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize:[25,41],iconAnchor:[12,41],popupAnchor:[1,-34],shadowSize:[41,41]
}});

var startM=null, endM=null, routeLine=null, step='start';
var routeDistKm=null, routeDurMin=null, isRoadRoute=false;

var initStart = {start_js};
var initEnd   = {end_js};
var initRoad  = {road_js};

if (initStart) placeMarker('start', initStart[0], initStart[1], '{start_name}');
if (initEnd)   placeMarker('end',   initEnd[0],   initEnd[1],   '{end_name}');
if (initRoad && initRoad.length > 1) {{ drawRoadLine(initRoad); step = 'done'; }}

var toast = document.getElementById('toast');
var spinner = document.getElementById('spinner');

function showToast(msg, color) {{
  toast.textContent = msg;
  toast.style.color = color || '#4ade80';
  toast.style.borderColor = color || '#22c55e';
  toast.style.opacity = '1';
}}

function haversine(a, b) {{
  var R=6371, dLat=(b[0]-a[0])*Math.PI/180, dLon=(b[1]-a[1])*Math.PI/180;
  var x=Math.sin(dLat/2)*Math.sin(dLat/2)+
        Math.cos(a[0]*Math.PI/180)*Math.cos(b[0]*Math.PI/180)*
        Math.sin(dLon/2)*Math.sin(dLon/2);
  return R*2*Math.atan2(Math.sqrt(x), Math.sqrt(1-x));
}}

function fmtDur(min) {{
  var h=Math.floor(min/60), m=Math.round(min%60);
  return h>0 ? h+'ч '+m+'мин' : m+' мин';
}}

function short(s) {{ return s && s.length>35 ? s.substring(0,34)+'…' : s||'—'; }}

function updatePanel() {{
  var sn = startM ? (startM._name||'') : '', en = endM ? (endM._name||'') : '';
  document.getElementById('sTxt').textContent = short(sn);
  document.getElementById('eTxt').textContent = short(en);
  if (routeDistKm !== null) {{
    document.getElementById('distTxt').textContent = routeDistKm.toFixed(1)+' km';
    document.getElementById('durTxt').textContent  = routeDurMin ? fmtDur(routeDurMin) : '—';
    document.getElementById('routeType').textContent =
      isRoadRoute ? '🛣️ По улиците' : '📐 Право (без интернет)';
  }}
}}

var currentProfile = 'driving';

function fetchRoute() {{
  if (!startM || !endM) return;
  var a=startM.getLatLng(), b=endM.getLatLng();
  spinner.style.display='block';
  var coords = a.lng+','+a.lat+';'+b.lng+','+b.lat;
  var url='https://router.project-osrm.org/route/v1/'+currentProfile+'/'+coords+'?overview=full&geometries=geojson';
  fetch(url)
    .then(r=>r.json())
    .then(function(data) {{
      spinner.style.display='none';
      if (data.code==='Ok') {{
        var route=data.routes[0];
        routeDistKm = route.distance/1000;
        routeDurMin = route.duration/60;
        isRoadRoute = true;
        drawRoadLine(route.geometry.coordinates.map(function(c){{return [c[1],c[0]];}}));
        showToast('✅ Маршрут: '+routeDistKm.toFixed(1)+' km', '#4ade80');
      }} else {{ fallbackStraightLine(); }}
      updatePanel();
    }})
    .catch(function() {{
      spinner.style.display='none';
      fallbackStraightLine();
      updatePanel();
    }});
}}

function drawRoadLine(coords) {{
  if (routeLine) map.removeLayer(routeLine);
  routeLine = L.polyline(coords, {{color:'#39ff14', weight:4, opacity:0.85}}).addTo(map);
  map.fitBounds(routeLine.getBounds(), {{padding:[50,50]}});
}}

function fallbackStraightLine() {{
  var a=startM.getLatLng(), b=endM.getLatLng();
  if (routeLine) map.removeLayer(routeLine);
  routeLine = L.polyline([[a.lat,a.lng],[b.lat,b.lng]], {{
    color:'#fbbf24', weight:3, dashArray:'8 6'
  }}).addTo(map);
  map.fitBounds(routeLine.getBounds(), {{padding:[50,50]}});
  routeDistKm = haversine([a.lat,a.lng],[b.lat,b.lng]);
  routeDurMin = null; isRoadRoute = false;
  showToast('⚠️ Право: '+routeDistKm.toFixed(1)+' km', '#fbbf24');
}}

function reverseGeocode(lat, lng, cb) {{
  fetch('https://nominatim.openstreetmap.org/reverse?format=json&lat='+lat+'&lon='+lng)
    .then(r=>r.json()).then(d=>cb(d.display_name||lat.toFixed(5)+', '+lng.toFixed(5)))
    .catch(()=>cb(lat.toFixed(5)+', '+lng.toFixed(5)));
}}

function placeMarker(type, lat, lng, name) {{
  if (type==='start') {{
    if (startM) map.removeLayer(startM);
    startM = L.marker([lat,lng],{{icon:greenIcon,draggable:true}})
               .addTo(map).bindPopup('<b>🟢 Начало</b><br>'+(name||''));
    startM._name = name||'';
    startM.on('dragend', function(e){{
      var p=e.target.getLatLng();
      reverseGeocode(p.lat,p.lng,function(n){{startM._name=n; fetchRoute(); updatePanel();}});
    }});
  }} else {{
    if (endM) map.removeLayer(endM);
    endM = L.marker([lat,lng],{{icon:redIcon,draggable:true}})
             .addTo(map).bindPopup('<b>🔴 Край</b><br>'+(name||''));
    endM._name = name||'';
    endM.on('dragend', function(e){{
      var p=e.target.getLatLng();
      reverseGeocode(p.lat,p.lng,function(n){{endM._name=n; fetchRoute(); updatePanel();}});
    }});
  }}
}}

map.on('click', function(e) {{
  var lat=e.latlng.lat, lng=e.latlng.lng;
  if (step==='start'||step==='done') {{
    reverseGeocode(lat,lng,function(name){{
      placeMarker('start',lat,lng,name); step='end';
      showToast('🔴 Кликни за крайна точка','#ef4444'); updatePanel();
    }});
  }} else if (step==='end') {{
    reverseGeocode(lat,lng,function(name){{
      placeMarker('end',lat,lng,name); step='done';
      showToast('⏳ Търся маршрут…','#fbbf24');
      fetchRoute(); updatePanel();
    }});
  }}
}});

function clearAll() {{
  if (startM) map.removeLayer(startM);
  if (endM)   map.removeLayer(endM);
  if (routeLine) map.removeLayer(routeLine);
  startM=endM=routeLine=null;
  routeDistKm=routeDurMin=null; isRoadRoute=false; step='start';
  ['sTxt','eTxt','distTxt','durTxt','routeType'].forEach(id=>
    document.getElementById(id).textContent='—');
  showToast('🟢 Кликни за начална точка','#4ade80');
}}

function sendRoute() {{
  if (!startM||!endM) {{ alert('Моля избери начало и край!'); return; }}
  var a=startM.getLatLng(), b=endM.getLatLng();
  fetch('http://127.0.0.1:{MAP_PORT}', {{
    method:'POST', headers:{{'Content-Type':'application/json'}},
    body: JSON.stringify({{
      start_lat:a.lat, start_lng:a.lng, start_name:startM._name,
      end_lat:b.lat,   end_lng:b.lng,   end_name:endM._name,
      road_dist_km:routeDistKm, road_dur_min:routeDurMin, is_road_route:isRoadRoute
    }})
  }}).then(()=>showToast('✅ Изпратено към ЕкоСледа!','#4ade80'))
    .catch(()=>alert('Не може да се свърже с ЕкоСледа.'));
}}
</script>
</body>
</html>"""
