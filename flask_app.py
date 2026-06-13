"""
flask_app.py — FitFindr with Three.js 3D orb + Claude Vision fit check
Run: python flask_app.py → http://127.0.0.1:5000
"""
import base64, json, os
from groq import Groq
from flask import Flask, request, jsonify, render_template_string
from agent import run_agent

app = Flask(__name__, static_folder='static')

def _load_wardrobes():
    schema_path = os.path.join(os.path.dirname(__file__), "data", "wardrobe_schema.json")
    with open(schema_path, encoding="utf-8") as f:
        data = json.load(f)
    return data["example_wardrobe"], data["empty_wardrobe"]

@app.route("/fit-check", methods=["POST"])
def fit_check():
    data = request.get_json()
    image_b64  = data.get("image")
    media_type = data.get("media_type", "image/jpeg")
    if not image_b64:
        return jsonify({"error": "No image provided."})
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return jsonify({"error": "GROQ_API_KEY not set in .env."})
    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            max_tokens=400,
            messages=[{"role":"user","content":[
                {"type":"image_url","image_url":{"url":f"data:{media_type};base64,{image_b64}"}},
                {"type":"text","text":(
                    "You are a fashion-forward stylist. Look at this photo and describe "
                    "what this person is wearing in specific detail: the pieces, colors, "
                    "fit, and overall vibe/aesthetic. Be concise — 3-5 sentences max. "
                    "Focus only on the clothing and style, not the person's appearance. "
                    "End with one sentence starting with 'Style vibe:' summarizing the aesthetic."
                )}
            ]}]
        )
        return jsonify({"analysis": response.choices[0].message.content.strip()})
    except Exception as e:
        return jsonify({"error": f"Vision analysis failed: {e}"})

@app.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    query          = (data.get("query") or "").strip()
    wardrobe_choice = data.get("wardrobe", "example")
    fit_context    = data.get("fit_context", "")
    if not query:
        return jsonify({"error": "Please enter a search query."})
    example_wardrobe, empty_wardrobe = _load_wardrobes()
    wardrobe = example_wardrobe if wardrobe_choice == "example" else empty_wardrobe
    augmented_query = query
    if fit_context:
        augmented_query = query + f"\n\n[User's current fit for context: {fit_context}]"
    session = run_agent(query=augmented_query, wardrobe=wardrobe)
    return jsonify(session)

@app.route("/")
def index():
    return render_template_string(HTML)


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FitFindr</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--cream:#FDF8F2;--ink:#1A1108;--coral:#FF5C3A;--lilac:#C8B8E8;--mint:#A8DDD1;--gold:#F2C94C;--blush:#F9D5C8;--mid:#6B5B4E}
html{scroll-behavior:smooth}
body{background:var(--cream);color:var(--ink);font-family:'DM Sans',sans-serif;font-weight:300;min-height:100vh;overflow-x:hidden}
header{display:flex;align-items:center;justify-content:space-between;padding:1.4rem 3rem;border-bottom:1.5px solid var(--ink);position:sticky;top:0;background:var(--cream);z-index:200}
.logo{font-family:'Playfair Display',serif;font-weight:900;font-size:1.7rem;letter-spacing:-0.02em;color:var(--ink);text-decoration:none}
.logo span{color:var(--coral);font-style:italic}
.tag-line{font-size:0.72rem;letter-spacing:0.18em;text-transform:uppercase;color:var(--mid)}
.hero{display:grid;grid-template-columns:1fr 1fr;min-height:90vh;border-bottom:1.5px solid var(--ink)}
.hero-left{padding:5rem 4rem;display:flex;flex-direction:column;justify-content:center;border-right:1.5px solid var(--ink)}
.eyebrow{font-size:0.68rem;letter-spacing:0.22em;text-transform:uppercase;color:var(--mid);margin-bottom:1.4rem}
h1{font-family:'Playfair Display',serif;font-weight:900;font-size:clamp(3rem,5vw,5.2rem);line-height:1;letter-spacing:-0.03em;margin-bottom:1.8rem}
h1 em{font-style:italic;color:var(--coral)}
.hero-sub{font-size:0.95rem;line-height:1.7;color:var(--mid);max-width:36ch;margin-bottom:2.5rem}
.search-block{display:flex;flex-direction:column;gap:0.9rem}
.input-wrap{display:flex;border:1.5px solid var(--ink);overflow:hidden;background:#fff}
.input-wrap input{flex:1;padding:1rem 1.2rem;font-family:'DM Sans',sans-serif;font-size:0.95rem;border:none;outline:none;background:transparent;color:var(--ink)}
.input-wrap input::placeholder{color:#bbb}
.btn-find{padding:1rem 2rem;background:var(--coral);color:#fff;border:none;font-family:'DM Sans',sans-serif;font-size:0.82rem;font-weight:500;letter-spacing:0.08em;text-transform:uppercase;cursor:pointer;transition:background 0.2s;white-space:nowrap}
.btn-find:hover{background:#e04a2a}
.btn-find:disabled{background:#ccc;cursor:not-allowed}
.wardrobe-toggle{display:flex;gap:0.6rem}
.toggle-btn{padding:0.5rem 1.1rem;border:1.5px solid var(--ink);background:transparent;font-family:'DM Sans',sans-serif;font-size:0.8rem;letter-spacing:0.06em;cursor:pointer;transition:all 0.15s;color:var(--ink)}
.toggle-btn.active{background:var(--ink);color:var(--cream)}
.examples{display:flex;flex-wrap:wrap;gap:0.5rem;margin-top:0.2rem}
.pill{padding:0.35rem 0.85rem;border:1px solid var(--mid);border-radius:999px;font-size:0.75rem;color:var(--mid);cursor:pointer;transition:all 0.15s;background:transparent;font-family:'DM Sans',sans-serif}
.pill:hover{border-color:var(--coral);color:var(--coral)}

/* FIT CHECK */
.fit-check-btn{display:inline-flex;align-items:center;gap:0.5rem;padding:0.6rem 1.2rem;border:1.5px solid var(--lilac);background:transparent;font-family:'DM Sans',sans-serif;font-size:0.8rem;letter-spacing:0.05em;cursor:pointer;color:var(--mid);transition:all 0.2s;align-self:flex-start}
.fit-check-btn:hover,.fit-check-btn.active{border-color:var(--coral);color:var(--coral);background:var(--blush)}
.fit-panel{display:none;flex-direction:column;gap:0.8rem;border:1.5px solid var(--lilac);padding:1.2rem;background:#fff}
.fit-panel.open{display:flex;animation:slideDown 0.2s ease}
@keyframes slideDown{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
.fit-panel-title{font-size:0.72rem;letter-spacing:0.18em;text-transform:uppercase;color:var(--mid)}
.fit-panel-actions{display:flex;gap:0.6rem;flex-wrap:wrap}
.fit-action-btn{padding:0.5rem 1rem;border:1.5px solid var(--ink);background:transparent;font-family:'DM Sans',sans-serif;font-size:0.78rem;cursor:pointer;color:var(--ink);transition:all 0.15s}
.fit-action-btn:hover{background:var(--ink);color:var(--cream)}
#tryOnWrap{display:none;flex-direction:column;gap:0.5rem}
#tryOnWrap.visible{display:flex}
#tryOnControls{display:none;flex-direction:column;gap:0.5rem}
#tryOnControls.visible{display:flex}
#tryOnCanvas{border:1.5px solid var(--ink);display:block;max-width:300px}
#fitAnalysis{font-size:0.82rem;line-height:1.65;color:var(--mid);display:none;border-left:3px solid var(--coral);padding-left:0.8rem;font-style:italic}
#fitAnalysis.visible{display:block}
#analysisLoader{font-size:0.78rem;color:var(--mid);display:none;letter-spacing:0.08em}
#analysisLoader.visible{display:block}
#cameraWrap{display:none;flex-direction:column;gap:0.6rem}
#cameraWrap.visible{display:flex}
#cameraVideo{width:100%;max-width:260px;border:1.5px solid var(--ink)}
.cam-snap-btn{padding:0.5rem 1.2rem;background:var(--coral);color:#fff;border:none;font-family:'DM Sans',sans-serif;font-size:0.8rem;cursor:pointer;align-self:flex-start}
.cam-snap-btn:hover{background:#e04a2a}

/* 3D HERO */
.hero-right{position:relative;background:linear-gradient(180deg,#C8B8E8 0%,#E2DDF0 55%,#E8E0D4 55%,#DDD4C8 100%);overflow:hidden}

/* LOADING */
#loading{display:none;padding:5rem 3rem;text-align:center;border-bottom:1.5px solid var(--ink)}
#loading.visible{display:block}
.loading-spinner{width:40px;height:40px;border:3px solid var(--lilac);border-top-color:var(--coral);border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto 1.5rem}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-text{font-family:'Playfair Display',serif;font-style:italic;font-size:1.2rem;color:var(--mid)}

/* RESULTS */
#results{display:none;padding:4rem 3rem;border-bottom:1.5px solid var(--ink)}
#results.visible{display:block}
.results-header{display:flex;align-items:baseline;gap:1.2rem;margin-bottom:2.5rem;border-bottom:1.5px solid var(--ink);padding-bottom:1rem}
.results-header h2{font-family:'Playfair Display',serif;font-size:2rem;font-weight:700}
.query-echo{font-style:italic;color:var(--coral)}
.cards-grid{display:grid;grid-template-columns:repeat(3,1fr);border:1.5px solid var(--ink)}
.card{padding:2rem;border-right:1.5px solid var(--ink)}
.card:last-child{border-right:none}
.card-num{font-size:0.62rem;letter-spacing:0.2em;text-transform:uppercase;color:var(--mid);margin-bottom:0.8rem}
.card-title{font-family:'Playfair Display',serif;font-weight:700;font-size:1.1rem;line-height:1.25;margin-bottom:1rem}
.card-body{font-size:0.88rem;line-height:1.7;color:var(--mid);white-space:pre-wrap}
.listing-meta{display:flex;flex-wrap:wrap;gap:0.4rem;margin-bottom:1rem}
.chip{padding:0.2rem 0.6rem;font-size:0.7rem;letter-spacing:0.06em;text-transform:uppercase;border:1px solid currentColor}
.chip-coral{color:var(--coral)}.chip-ink{color:var(--ink)}.chip-mid{color:var(--mid)}
.price-big{font-family:'Playfair Display',serif;font-size:2.4rem;font-weight:900;line-height:1;margin-bottom:0.6rem;color:var(--coral)}
.card-3{background:var(--ink);color:var(--cream)}
.card-3 .card-num{color:var(--lilac)}.card-3 .card-title{color:var(--cream)}.card-3 .card-body{color:#c8bfb8}
.error-card{border:1.5px solid var(--coral);padding:2.5rem;display:flex;gap:1.5rem;align-items:flex-start}
.error-icon{font-size:2rem;flex-shrink:0}
.error-title{font-family:'Playfair Display',serif;font-weight:700;font-size:1.2rem;margin-bottom:0.5rem;color:var(--coral)}
.error-msg{font-size:0.9rem;line-height:1.7;color:var(--mid)}

/* HOW */
.how{display:grid;grid-template-columns:repeat(3,1fr);border-top:1.5px solid var(--ink)}
.how-step{padding:3rem 2.5rem;border-right:1.5px solid var(--ink)}
.how-step:last-child{border-right:none}
.how-num{display:inline-block;width:36px;height:36px;border:1.5px solid var(--ink);border-radius:50%;text-align:center;line-height:33px;font-size:0.78rem;font-weight:500;margin-bottom:1.2rem}
.how-step h3{font-family:'Playfair Display',serif;font-size:1.1rem;font-weight:700;margin-bottom:0.7rem}
.how-step p{font-size:0.85rem;line-height:1.7;color:var(--mid)}
footer{padding:1.4rem 3rem;border-top:1.5px solid var(--ink);display:flex;justify-content:space-between;align-items:center;font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;color:var(--mid)}

@media(max-width:860px){
  .hero{grid-template-columns:1fr}
  .hero-right{height:320px}
  .hero-left{padding:3rem 1.5rem;border-right:none;border-bottom:1.5px solid var(--ink)}
  .cards-grid{grid-template-columns:1fr}
  .card{border-right:none;border-bottom:1.5px solid var(--ink)}
  .how{grid-template-columns:1fr}
  .how-step{border-right:none;border-bottom:1.5px solid var(--ink)}
  header,#results,#loading{padding-left:1.5rem;padding-right:1.5rem}
}
</style>
</head>
<body>

<header>
  <a class="logo" href="#">Fit<span>Findr</span></a>
  <span class="tag-line">AI-powered thrift styling</span>
</header>

<section class="hero">
  <div class="hero-left">
    <p class="eyebrow">Secondhand · Styled · Shareable</p>
    <h1>Find your<br><em>next</em><br>thrift fit.</h1>
    <p class="hero-sub">Tell us what you're hunting for. We'll find the piece, build the outfit, and write the caption.</p>
    <div class="search-block">
      <div class="input-wrap">
        <input type="text" id="query" placeholder="vintage graphic tee under $30, size M"/>
        <button class="btn-find" id="findBtn" onclick="doSearch()">Find it →</button>
      </div>
      <div class="wardrobe-toggle">
        <button class="toggle-btn active" id="togEx" onclick="setWardrobe('example')">My wardrobe</button>
        <button class="toggle-btn" id="togEm" onclick="setWardrobe('empty')">New user</button>
      </div>

      <button class="fit-check-btn" id="fitCheckBtn" onclick="toggleFitPanel()">
        <span>📸</span> Fit Check — show us what you're wearing
      </button>
      <div class="fit-panel" id="fitPanel">
        <div class="fit-panel-title">📸 Drop a photo or snap — try on outfits instantly</div>
        <div class="fit-panel-actions">
          <label class="fit-action-btn" for="fitUpload">📁 Upload photo</label>
          <input type="file" id="fitUpload" accept="image/*" style="display:none" onchange="handleUpload(event)">
          <button class="fit-action-btn" onclick="startCamera()">📷 Camera</button>
          <button class="fit-action-btn" id="clearFitBtn" onclick="clearFit()" style="display:none">✕ Clear</button>
        </div>
        <div id="cameraWrap">
          <video id="cameraVideo" autoplay playsinline></video>
          <canvas id="snapCanvas" style="display:none"></canvas>
          <button class="cam-snap-btn" onclick="snapPhoto()">Snap ✦</button>
        </div>
        <!-- Try-on canvas -->
        <div id="tryOnWrap" style="display:none;flex-direction:column;gap:0.5rem">
          <canvas id="tryOnCanvas" style="border:1.5px solid var(--ink);display:block;max-width:300px"></canvas>
        </div>
        <!-- Try-on controls -->
        <div id="tryOnControls" style="display:none;flex-direction:column;gap:0.5rem">
          <button class="fit-action-btn" id="tryOnBtn" onclick="toggleTryOn()">👗 Try on outfit</button>
          <div style="display:flex;align-items:center;gap:0.6rem">
            <button class="fit-action-btn" onclick="switchOutfit(-1)" style="padding:0.3rem 0.7rem">←</button>
            <span id="outfitName" style="font-size:0.78rem;color:var(--mid);letter-spacing:0.05em">Coral Jacket + Jeans</span>
            <button class="fit-action-btn" onclick="switchOutfit(1)" style="padding:0.3rem 0.7rem">→</button>
          </div>
        </div>
        <div id="analysisLoader">Analyzing your fit…</div>
        <div id="fitAnalysis"></div>
      </div>

      <div class="examples">
        <span class="eyebrow" style="align-self:center;margin-bottom:0;margin-right:0.4rem">Try:</span>
        <button class="pill" onclick="fillQuery('90s track jacket size M')">90s track jacket size M</button>
        <button class="pill" onclick="fillQuery('flowy midi skirt under $40')">midi skirt under $40</button>
        <button class="pill" onclick="fillQuery('black combat boots size 8')">combat boots size 8</button>
        <button class="pill" onclick="fillQuery('designer ballgown size XXS under $5')">impossible →</button>
      </div>
    </div>
  </div>
  <div class="hero-right" id="heroScene">
    <canvas id="threeCanvas" style="width:100%;height:100%;display:block;cursor:grab"></canvas>
    <div style="position:absolute;bottom:1.2rem;left:50%;transform:translateX(-50%);font-size:0.6rem;letter-spacing:0.18em;text-transform:uppercase;color:#6B5B4E;opacity:0.5;white-space:nowrap;font-family:DM Sans,sans-serif">drag to rotate</div>
  </div>
</section>

<div id="loading">
  <div class="loading-spinner"></div>
  <p class="loading-text" id="loadingText">Searching the racks…</p>
</div>

<section id="results">
  <div class="results-header">
    <h2>Results for</h2>
    <h2 class="query-echo" id="queryEcho">"…"</h2>
  </div>
  <div id="resultsContent"></div>
</section>

<section class="how">
  <div class="how-step"><div class="how-num">1</div><h3>Search listings</h3><p>We scan 40 mock secondhand listings and score them by keyword match — filtering by your size and budget.</p></div>
  <div class="how-step"><div class="how-num">2</div><h3>Build the outfit</h3><p>Our AI pairs the find with pieces from your wardrobe — naming specific items and giving real styling tips.</p></div>
  <div class="how-step"><div class="how-num">3</div><h3>Write the caption</h3><p>Get a ready-to-post fit card that sounds like a real OOTD post — not a product description.</p></div>
</section>

<footer>
  <span>FitFindr · AI 201 Project</span>
  <span>Powered by Groq · llama-4-scout vision</span>
</footer>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
/* ── THREE.JS MANNEQUIN + PHOTO CARDS ── */
(function(){
  var canvas = document.getElementById('threeCanvas');
  if(!canvas) return;
  var parent = canvas.parentElement;

  var renderer = new THREE.WebGLRenderer({canvas:canvas, antialias:true, alpha:false});
  renderer.setPixelRatio(Math.min(window.devicePixelRatio,2));
  renderer.shadowMap.enabled = true;
  renderer.setClearColor(0xC8B8E8, 1);

  var scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0xC8B8E8, 12, 24);

  var camera = new THREE.PerspectiveCamera(40, 1, 0.1, 50);
  camera.position.set(0, 0.5, 8);

  // Lights
  scene.add(new THREE.AmbientLight(0xfff8f0, 0.85));
  var sun = new THREE.DirectionalLight(0xfff5e0, 1.2);
  sun.position.set(4, 8, 6); sun.castShadow = true; scene.add(sun);
  var fill = new THREE.DirectionalLight(0xC8B8E8, 0.5);
  fill.position.set(-4, 2, -4); scene.add(fill);

  /* ── MANNEQUIN ── */
  var mGroup = new THREE.Group();
  var cream = new THREE.MeshPhongMaterial({color:0xF5F0E8, specular:0x888888, shininess:60});
  var dark  = new THREE.MeshPhongMaterial({color:0x1A1108, specular:0xaaaaaa, shininess:80});

  // Torso — tapered cylinder
  var torso = new THREE.Mesh(new THREE.CylinderGeometry(0.40,0.32,1.05,24), cream);
  mGroup.add(torso);
  // Chest curve
  var chest = new THREE.Mesh(new THREE.SphereGeometry(0.38,18,12,0,Math.PI*2,0,Math.PI/2), cream);
  chest.position.y = 0.42; chest.scale.y = 0.55; mGroup.add(chest);
  // Shoulder bar
  var shGeo = new THREE.CylinderGeometry(0.055,0.055,1.0,12);
  shGeo.rotateZ(Math.PI/2);
  var sh = new THREE.Mesh(shGeo, cream); sh.position.y = 0.50; mGroup.add(sh);
  // Neck
  var neck = new THREE.Mesh(new THREE.CylinderGeometry(0.09,0.12,0.28,14), cream);
  neck.position.y = 0.66; mGroup.add(neck);
  // Head
  var head = new THREE.Mesh(new THREE.SphereGeometry(0.21,20,20), cream);
  head.position.y = 0.97; mGroup.add(head);
  // Hip
  var hip = new THREE.Mesh(new THREE.CylinderGeometry(0.36,0.30,0.32,20), cream);
  hip.position.y = -0.66; mGroup.add(hip);
  // Waist seam
  var seam = new THREE.Mesh(new THREE.TorusGeometry(0.36,0.018,8,40), new THREE.MeshPhongMaterial({color:0xDDD8D0,shininess:20}));
  seam.rotation.x = Math.PI/2; seam.position.y = -0.50; mGroup.add(seam);
  // Stand rod
  var rod = new THREE.Mesh(new THREE.CylinderGeometry(0.038,0.038,1.4,12), dark);
  rod.position.y = -1.42; mGroup.add(rod);
  // Base
  var base = new THREE.Mesh(new THREE.CylinderGeometry(0.52,0.52,0.07,32), dark);
  base.position.y = -2.12; mGroup.add(base);
  // Wireframe lines on torso for that fashion dummy look
  var wireGeo = new THREE.CylinderGeometry(0.41,0.33,1.05,10);
  var wireMesh = new THREE.Mesh(wireGeo, new THREE.MeshBasicMaterial({color:0xD0C8C0,wireframe:true,opacity:0.12,transparent:true}));
  mGroup.add(wireMesh);

  // Floor shadow disc
  var shadow = new THREE.Mesh(
    new THREE.CircleGeometry(1.2,32),
    new THREE.MeshBasicMaterial({color:0x000000,opacity:0.08,transparent:true})
  );
  shadow.rotation.x = -Math.PI/2; shadow.position.y = -2.16; scene.add(shadow);

  scene.add(mGroup);

  /* ── PHOTO CARDS orbiting the mannequin ── */
  var loader = new THREE.TextureLoader();
  loader.crossOrigin = 'anonymous';

  var photoItems = [
    { url:'https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=300&h=380&fit=crop&auto=format&q=80', label:'Jacket',  angle:0,            radius:2.8, yw:0.3,  spd:0.006 },
    { url:'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=300&h=380&fit=crop&auto=format&q=80', label:'Shirt',   angle:Math.PI*0.4,  radius:2.7, yw:0.1,  spd:0.005 },
    { url:'https://images.unsplash.com/photo-1544923246-77307dd654cb?w=300&h=380&fit=crop&auto=format&q=80', label:'Coat',    angle:Math.PI*0.8,  radius:2.9, yw:-0.1, spd:0.0055},
    { url:'https://images.unsplash.com/photo-1612336307429-8a898d10e223?w=300&h=380&fit=crop&auto=format&q=80', label:'Dress',   angle:Math.PI*1.2,  radius:2.7, yw:0.2,  spd:0.006 },
    { url:'/static/hoodie.png',                                                                                  label:'Hoodie',  angle:Math.PI*1.6,  radius:2.8, yw:0.0,  spd:0.0065},
    { url:'https://images.unsplash.com/photo-1564257631407-4deb1f99d992?w=300&h=380&fit=crop&auto=format&q=80', label:'Blouse',  angle:Math.PI*2.0,  radius:2.6, yw:0.15, spd:0.005 },
    { url:'https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=300&h=380&fit=crop&auto=format&q=80', label:'Blazer',  angle:Math.PI*2.4,  radius:2.8, yw:-0.2, spd:0.0058},
  ];

  var cards = [];
  var lineMat = new THREE.LineDashedMaterial({color:0x8B7B6E, dashSize:0.08, gapSize:0.06, opacity:0.3, transparent:true});

  photoItems.forEach(function(item){
    var group = new THREE.Group();

    // Card frame — slightly thick plane
    var frameGeo = new THREE.BoxGeometry(0.82, 1.05, 0.04);
    var frameMat = new THREE.MeshPhongMaterial({color:0xFDF8F2, shininess:30});
    var frame = new THREE.Mesh(frameGeo, frameMat);
    frame.castShadow = true;
    group.add(frame);

    // Photo plane slightly in front of frame
    var photoGeo = new THREE.PlaneGeometry(0.72, 0.92);
    var tex = loader.load(item.url);
    tex.minFilter = THREE.LinearFilter;
    var photoMat = new THREE.MeshBasicMaterial({map:tex, transparent:false});
    var photo = new THREE.Mesh(photoGeo, photoMat);
    photo.position.z = 0.023;
    group.add(photo);

    // Thin top edge — hanger illusion
    var edgeGeo = new THREE.BoxGeometry(0.82, 0.04, 0.06);
    var edge = new THREE.Mesh(edgeGeo, new THREE.MeshPhongMaterial({color:0x9B7B58, shininess:60}));
    edge.position.y = 0.545; group.add(edge);

    // Dashed line to mannequin
    var pts = [new THREE.Vector3(0,0,0), new THREE.Vector3(0,0,0)];
    var lineGeo = new THREE.BufferGeometry().setFromPoints(pts);
    var line = new THREE.Line(lineGeo, lineMat);
    line.computeLineDistances();
    scene.add(line);

    group.userData = {
      angle: item.angle, radius: item.radius, baseY: item.yw,
      speed: item.spd, line: line, floatOff: Math.random()*Math.PI*2
    };
    group.scale.setScalar(0.9);
    scene.add(group);
    cards.push(group);
  });

  /* ── Floor grid ── */
  var grid = new THREE.GridHelper(14, 18, 0x8B7B6E, 0x8B7B6E);
  grid.material.opacity = 0.07; grid.material.transparent = true;
  grid.position.y = -2.18; scene.add(grid);

  /* ── Mouse drag ── */
  var drag = false, lx = 0, velY = 0, rotY = 0;
  canvas.addEventListener('mousedown',  function(e){drag=true; lx=e.clientX;});
  window.addEventListener('mouseup',   function(){drag=false;});
  window.addEventListener('mousemove', function(e){
    if(!drag) return;
    velY = (e.clientX - lx) * 0.010; lx = e.clientX;
  });
  canvas.addEventListener('touchstart', function(e){drag=true; lx=e.touches[0].clientX;},{passive:true});
  window.addEventListener('touchend',   function(){drag=false;});
  window.addEventListener('touchmove',  function(e){
    if(!drag) return;
    velY=(e.touches[0].clientX-lx)*0.010; lx=e.touches[0].clientX;
  },{passive:true});

  function resize(){
    var w=parent.offsetWidth, h=Math.max(parent.offsetHeight,420);
    renderer.setSize(w,h);
    camera.aspect = w/h;
    camera.updateProjectionMatrix();
  }
  resize(); window.addEventListener('resize', resize);

  var t = 0;
  function animate(){
    requestAnimationFrame(animate); t += 0.009;
    if(!drag){ velY *= 0.90; rotY += 0.004; }
    rotY += velY; velY *= 0.86;

    mGroup.rotation.y = rotY * 0.15;
    mGroup.position.y = Math.sin(t*0.5) * 0.03;

    cards.forEach(function(card){
      var d = card.userData;
      d.angle += d.speed;
      var a = d.angle + rotY;
      card.position.x = Math.cos(a) * d.radius;
      card.position.z = Math.sin(a) * d.radius * 0.5;
      card.position.y = d.baseY + Math.sin(t*0.6 + d.floatOff) * 0.18;
      // Cards always face camera
      card.rotation.y = -a + Math.PI * 0.5;
      // Gentle tilt
      card.rotation.x = Math.sin(t*0.4 + d.floatOff) * 0.05;

      // Update dashed line
      var ln = d.line;
      var pts = [
        new THREE.Vector3(mGroup.position.x, mGroup.position.y + 0.3, mGroup.position.z),
        card.position.clone()
      ];
      ln.geometry.setFromPoints(pts);
      ln.computeLineDistances();
    });

    renderer.render(scene, camera);
  }
  animate();
})();
</script>

<script>
/* ── All functions at global scope so onclick= attributes work ── */

// Photo sizes increased
var _RACK_PHOTO_W = 96, _RACK_PHOTO_H = 132;

/* ── State ── */
var fitB64=null, fitType='image/jpeg', fitText='', camStream=null;
var tryOnActive=false, selectedOutfit=0;
var wardrobe='example';
var loadInt;
var OUTFITS=[
  {label:'Coral Jacket + Jeans',      topColor:'#FF5C3A',bottomColor:'#2a4080'},
  {label:'Cream Shirt + Blush Skirt', topColor:'#F5F0E8',bottomColor:'#F9D5C8'},
  {label:'Mint Coat + Black Trousers',topColor:'#A8DDD1',bottomColor:'#1A1108'},
  {label:'Gold Top + Dark Jeans',     topColor:'#F2C94C',bottomColor:'#2a4080'},
];

/* ── Fit panel toggle ── */
function toggleFitPanel(){
  var p=document.getElementById('fitPanel');
  var b=document.getElementById('fitCheckBtn');
  p.classList.toggle('open');
  b.classList.toggle('active', p.classList.contains('open'));
}

/* ── Wardrobe ── */
function setWardrobe(w){
  wardrobe=w;
  document.getElementById('togEx').classList.toggle('active',w==='example');
  document.getElementById('togEm').classList.toggle('active',w==='empty');
}

/* ── Queries ── */
function fillQuery(t){
  document.getElementById('query').value=t;
  document.getElementById('query').focus();
}

/* ── Upload ── */
function handleUpload(e){
  var f=e.target.files[0]; if(!f)return;
  fitType=f.type||'image/jpeg';
  var r=new FileReader();
  r.onload=function(ev){
    var d=ev.target.result;
    fitB64=d.split(',')[1];
    showPreview(d);
    analyzeImage();
  };
  r.readAsDataURL(f);
}

/* ── Camera ── */
function startCamera(){
  if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){
    alert('Camera not supported in this browser.');return;
  }
  navigator.mediaDevices.getUserMedia({video:{facingMode:'user'}})
    .then(function(s){
      camStream=s;
      document.getElementById('cameraVideo').srcObject=s;
      document.getElementById('cameraWrap').classList.add('visible');
    })
    .catch(function(err){ alert('Camera access denied: '+err.message); });
}
function snapPhoto(){
  var v=document.getElementById('cameraVideo');
  var c=document.getElementById('snapCanvas');
  c.width=v.videoWidth; c.height=v.videoHeight;
  c.getContext('2d').drawImage(v,0,0);
  fitType='image/jpeg';
  var dataUrl=c.toDataURL('image/jpeg',0.9);
  fitB64=dataUrl.split(',')[1];
  showPreview(dataUrl);
  stopCamera();
  analyzeImage();
}
function stopCamera(){
  if(camStream){camStream.getTracks().forEach(function(t){t.stop();});camStream=null;}
  document.getElementById('cameraWrap').classList.remove('visible');
}

/* ── Preview + try-on ── */
function showPreview(src){
  var canvas=document.getElementById('tryOnCanvas');
  var img=new Image();
  img.onload=function(){
    var maxW=300,maxH=420;
    var scale=Math.min(maxW/img.width, maxH/img.height, 1);
    canvas.width=Math.round(img.width*scale);
    canvas.height=Math.round(img.height*scale);
    canvas.getContext('2d').drawImage(img,0,0,canvas.width,canvas.height);
    canvas.dataset.src=src;
    document.getElementById('tryOnWrap').classList.add('visible');
    document.getElementById('tryOnControls').classList.add('visible');
    document.getElementById('clearFitBtn').style.display='';
    if(tryOnActive) drawOverlay(canvas.getContext('2d'),canvas.width,canvas.height);
  };
  img.src=src;
}
function drawOverlay(ctx,w,h){
  var o=OUTFITS[selectedOutfit];
  ctx.save();
  // Top garment silhouette
  ctx.globalAlpha=0.42;
  ctx.fillStyle=o.topColor;
  var tx=w*0.18,ty=h*0.22,tw=w*0.64,th=h*0.30;
  ctx.beginPath();
  ctx.moveTo(tx+tw*0.12,ty);
  ctx.lineTo(tx+tw,ty+th*0.08);
  ctx.lineTo(tx+tw+tw*0.08,ty+th*0.3);
  ctx.lineTo(tx+tw,ty+th);
  ctx.lineTo(tx,ty+th);
  ctx.lineTo(tx-tw*0.08,ty+th*0.3);
  ctx.lineTo(tx,ty+th*0.08);
  ctx.closePath(); ctx.fill();
  // Bottom garment
  ctx.globalAlpha=0.40;
  ctx.fillStyle=o.bottomColor;
  ctx.beginPath();
  ctx.moveTo(w*0.22,h*0.52);
  ctx.lineTo(w*0.78,h*0.52);
  ctx.lineTo(w*0.84,h*0.92);
  ctx.lineTo(w*0.16,h*0.92);
  ctx.closePath(); ctx.fill();
  // Label
  ctx.globalAlpha=0.90;
  ctx.fillStyle='#1A1108';
  ctx.fillRect(4,4,192,24);
  ctx.fillStyle='#FDF8F2';
  ctx.font='bold 12px DM Sans, sans-serif';
  ctx.fillText('Try-on: '+o.label, 10, 20);
  ctx.restore();
}
function toggleTryOn(){
  tryOnActive=!tryOnActive;
  var btn=document.getElementById('tryOnBtn');
  btn.textContent=tryOnActive?'Remove try-on':'Try on outfit';
  btn.style.background=tryOnActive?'#1A1108':'';
  btn.style.color=tryOnActive?'#FDF8F2':'';
  redrawCanvas();
}
function switchOutfit(dir){
  selectedOutfit=(selectedOutfit+dir+OUTFITS.length)%OUTFITS.length;
  document.getElementById('outfitName').textContent=OUTFITS[selectedOutfit].label;
  if(tryOnActive) redrawCanvas();
}
function redrawCanvas(){
  var canvas=document.getElementById('tryOnCanvas');
  var src=canvas.dataset.src; if(!src)return;
  var img=new Image();
  img.onload=function(){
    var ctx=canvas.getContext('2d');
    ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.drawImage(img,0,0,canvas.width,canvas.height);
    if(tryOnActive) drawOverlay(ctx,canvas.width,canvas.height);
  };
  img.src=src;
}
function clearFit(){
  fitB64=null; fitText=''; tryOnActive=false;
  document.getElementById('tryOnWrap').classList.remove('visible');
  document.getElementById('tryOnControls').classList.remove('visible');
  document.getElementById('fitAnalysis').classList.remove('visible');
  document.getElementById('fitAnalysis').textContent='';
  document.getElementById('clearFitBtn').style.display='none';
  document.getElementById('fitUpload').value='';
  var btn=document.getElementById('tryOnBtn');
  if(btn){btn.textContent='Try on outfit';btn.style.background='';btn.style.color='';}
  stopCamera();
}
async function analyzeImage(){
  document.getElementById('analysisLoader').classList.add('visible');
  document.getElementById('fitAnalysis').classList.remove('visible');
  try{
    var resp=await fetch('/fit-check',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({image:fitB64,media_type:fitType})
    });
    var d=await resp.json();
    fitText=d.error?'':(d.analysis||'');
    document.getElementById('fitAnalysis').textContent=d.error?('Warning: '+d.error):('Style read: '+d.analysis);
    document.getElementById('fitAnalysis').classList.add('visible');
  }catch(err){
    document.getElementById('fitAnalysis').textContent='Could not analyze image.';
    document.getElementById('fitAnalysis').classList.add('visible');
  }
  document.getElementById('analysisLoader').classList.remove('visible');
}

/* ── Search ── */
function showLoading(q){
  document.getElementById('results').classList.remove('visible');
  document.getElementById('loading').classList.add('visible');
  document.getElementById('queryEcho').textContent='"'+q+'"';
  var msgs=['Searching the racks...','Matching your wardrobe...','Writing the caption...','Almost there...'];
  var i=0;
  document.getElementById('loadingText').textContent=msgs[0];
  loadInt=setInterval(function(){i=(i+1)%msgs.length;document.getElementById('loadingText').textContent=msgs[i];},1800);
}
function hideLoading(){clearInterval(loadInt);document.getElementById('loading').classList.remove('visible');}
function chip(t,cls){return '<span class="chip '+cls+'">'+t+'</span>';}
function renderResults(data,query){
  hideLoading();
  var el=document.getElementById('resultsContent');
  if(data.error){
    el.innerHTML='<div class="error-card"><div class="error-icon">&#x2756;</div><div><div class="error-title">Nothing found</div><div class="error-msg">'+data.error+'</div></div></div>';
  } else {
    var item=data.selected_item;
    var price=item.price?'$'+parseFloat(item.price).toFixed(0):'--';
    var plat=(item.platform||'');
    plat=plat.charAt(0).toUpperCase()+plat.slice(1);
    var cond=(item.condition||'');
    cond=cond.charAt(0).toUpperCase()+cond.slice(1);
    var colors=(item.colors&&item.colors.length)?item.colors.join(', '):'';
    el.innerHTML='<div class="cards-grid">'
      +'<div class="card">'
        +'<div class="card-num">01 -- The Find</div>'
        +'<div class="price-big">'+price+'</div>'
        +'<div class="card-title">'+(item.title||'Found item')+'</div>'
        +'<div class="listing-meta">'+chip(plat,'chip-coral')+chip(cond,'chip-ink')+(item.size?chip(item.size,'chip-mid'):'')+(colors?chip(colors,'chip-mid'):'')+(item.brand?chip(item.brand,'chip-mid'):'')+'</div>'
        +'<div class="card-body">'+(item.description||'')+'</div>'
      +'</div>'
      +'<div class="card">'
        +'<div class="card-num">02 -- The Outfit</div>'
        +'<div class="card-title">How to wear it</div>'
        +'<div class="card-body">'+(data.outfit_suggestion||'')+'</div>'
      +'</div>'
      +'<div class="card card-3">'
        +'<div class="card-num">03 -- Fit Card</div>'
        +'<div class="card-title">Your caption</div>'
        +'<div class="card-body">'+(data.fit_card||'')+'</div>'
      +'</div>'
      +'</div>';
  }
  document.getElementById('results').classList.add('visible');
  document.getElementById('results').scrollIntoView({behavior:'smooth',block:'start'});
}
async function doSearch(){
  var q=document.getElementById('query').value.trim();
  if(!q)return;
  document.getElementById('findBtn').disabled=true;
  showLoading(q);
  try{
    var resp=await fetch('/search',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({query:q,wardrobe:wardrobe,fit_context:fitText})
    });
    renderResults(await resp.json(),q);
  }catch(e){
    hideLoading();
    document.getElementById('resultsContent').innerHTML='<div class="error-card"><div class="error-icon">&#x2756;</div><div><div class="error-title">Server error</div><div class="error-msg">Make sure flask_app.py is running.</div></div></div>';
    document.getElementById('results').classList.add('visible');
  }finally{
    document.getElementById('findBtn').disabled=false;
  }
}

/* ── Rack + DOM init ── */
document.addEventListener('DOMContentLoaded', function(){
  // Enter key on search
  document.getElementById('query').addEventListener('keydown',function(e){
    if(e.key==='Enter') doSearch();
  });

  // Build clothing rack
  var panel=document.getElementById('rackPanel');
  if(!panel) return;

  var garments=[
    {label:'Jacket', img:'https://images.unsplash.com/photo-1591047139829-d91aecb6caea?w=220&h=300&fit=crop&auto=format&q=80', tilt:-2},
    {label:'Shirt',  img:'https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=220&h=300&fit=crop&auto=format&q=80', tilt:1},
    {label:'Coat',   img:'https://images.unsplash.com/photo-1544923246-77307dd654cb?w=220&h=300&fit=crop&auto=format&q=80', tilt:-1},
    {label:'Dress',  img:'https://images.unsplash.com/photo-1612336307429-8a898d10e223?w=220&h=300&fit=crop&auto=format&q=80', tilt:2},
    {label:'Hoodie', img:'https://images.unsplash.com/photo-1556821840-3a63f15732ce?w=220&h=300&fit=crop&auto=format&q=80', tilt:-2},
    {label:'Blouse', img:'https://images.unsplash.com/photo-1564257631407-4deb1f99d992?w=220&h=300&fit=crop&auto=format&q=80', tilt:1},
    {label:'Blazer', img:'https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=220&h=300&fit=crop&auto=format&q=80', tilt:-1},
  ];
  var woodCols=['#8B5E3C','#7a4e28','#9a6e3c','#6a4020','#8a5e38','#795030','#9b6830'];

  function hsvg(col){
    return '<svg viewBox="0 0 72 42" fill="none" xmlns="http://www.w3.org/2000/svg" style="width:72px;height:42px">'
      +'<path d="M36 6 Q36 1 41 1 Q46 1 46 6 Q46 12 36 16" stroke="#c0a878" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
      +'<path d="M36 16 Q21 18 9 26" stroke="'+col+'" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
      +'<path d="M36 16 Q51 18 63 26" stroke="'+col+'" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
      +'<line x1="9" y1="26" x2="63" y2="26" stroke="'+col+'" stroke-width="3.5" stroke-linecap="round"/>'
      +'<circle cx="9" cy="26" r="3.5" fill="#5a3a18"/>'
      +'<circle cx="63" cy="26" r="3.5" fill="#5a3a18"/>'
      +'</svg>';
  }

  panel.style.cssText='position:relative;overflow:hidden;background:linear-gradient(180deg,#C8B8E8 0%,#DDD6F0 52%,#E4DDD0 52%,#D8D0C0 100%)';
  panel.innerHTML=''
    +'<div style="position:absolute;top:26%;left:5%;right:5%;height:13px;background:linear-gradient(180deg,#ddd0b8,#b09878,#c8b090);border-radius:7px;box-shadow:0 5px 18px rgba(0,0,0,0.2),inset 0 2px 3px rgba(255,255,255,0.3);z-index:4"></div>'
    +'<div style="position:absolute;top:26%;left:5%;width:22px;height:22px;border-radius:50%;background:radial-gradient(circle at 35% 35%,#d4b888,#8a6840);transform:translate(-50%,-25%);box-shadow:0 2px 8px rgba(0,0,0,0.3);z-index:5"></div>'
    +'<div style="position:absolute;top:26%;right:5%;width:22px;height:22px;border-radius:50%;background:radial-gradient(circle at 35% 35%,#d4b888,#8a6840);transform:translate(50%,-25%);box-shadow:0 2px 8px rgba(0,0,0,0.3);z-index:5"></div>'
    +'<div style="position:absolute;top:26%;left:6.5%;width:11px;height:58%;background:linear-gradient(90deg,#ccc0a0,#a89070,#ccc0a0);border-radius:6px;box-shadow:3px 0 10px rgba(0,0,0,0.12);z-index:3"></div>'
    +'<div style="position:absolute;top:26%;right:6.5%;width:11px;height:58%;background:linear-gradient(90deg,#ccc0a0,#a89070,#ccc0a0);border-radius:6px;box-shadow:3px 0 10px rgba(0,0,0,0.12);z-index:3"></div>'
    +'<div style="position:absolute;bottom:6%;left:3%;width:13%;height:10px;background:linear-gradient(180deg,#b09878,#906848);border-radius:5px;box-shadow:0 4px 14px rgba(0,0,0,0.2);z-index:3"></div>'
    +'<div style="position:absolute;bottom:6%;right:3%;width:13%;height:10px;background:linear-gradient(180deg,#b09878,#906848);border-radius:5px;box-shadow:0 4px 14px rgba(0,0,0,0.2);z-index:3"></div>'
    +'<div id="gRow" style="position:absolute;top:26%;left:5%;right:5%;display:flex;align-items:flex-start;z-index:5;cursor:grab;padding:0 10px;gap:8px;will-change:transform"></div>'
    +'<div style="position:absolute;bottom:7%;left:15%;right:15%;height:16px;background:radial-gradient(ellipse,rgba(0,0,0,0.10),transparent 70%);z-index:2"></div>'
    +'<div style="position:absolute;bottom:1.2rem;left:50%;transform:translateX(-50%);font-size:0.6rem;letter-spacing:0.18em;text-transform:uppercase;color:#6B5B4E;opacity:0.5;white-space:nowrap;font-family:DM Sans,sans-serif;z-index:6">drag to browse</div>';

  var row=document.getElementById('gRow');
  garments.forEach(function(g,i){
    var wrap=document.createElement('div');
    wrap.style.cssText='display:flex;flex-direction:column;align-items:center;flex-shrink:0;width:112px;transform-origin:top center;transform:rotate('+g.tilt+'deg);transition:transform 0.25s ease,filter 0.25s ease;cursor:pointer';

    var hangerDiv=document.createElement('div');
    hangerDiv.style.cssText='width:72px;height:42px;flex-shrink:0';
    hangerDiv.innerHTML=hsvg(woodCols[i]);

    var photoDiv=document.createElement('div');
    // BIGGER photos: 96x132
    photoDiv.style.cssText='width:96px;height:132px;overflow:hidden;border-radius:1px;box-shadow:0 6px 20px rgba(0,0,0,0.22),0 2px 6px rgba(0,0,0,0.14);position:relative;margin-top:-2px;flex-shrink:0';
    var img=document.createElement('img');
    img.src=g.img; img.alt=g.label; img.loading='lazy';
    img.style.cssText='width:100%;height:100%;object-fit:cover;display:block;filter:saturate(1.08) contrast(1.04)';
    img.onerror=function(){this.parentElement.style.background='#c8b8a8';};
    var foldShadow=document.createElement('div');
    foldShadow.style.cssText='position:absolute;top:0;left:0;right:0;height:14px;background:linear-gradient(180deg,rgba(0,0,0,0.2),transparent);z-index:2;pointer-events:none';
    var crease=document.createElement('div');
    crease.style.cssText='position:absolute;top:0;bottom:0;left:0;width:3px;background:linear-gradient(90deg,rgba(0,0,0,0.1),transparent);z-index:2;pointer-events:none';
    photoDiv.appendChild(img); photoDiv.appendChild(foldShadow); photoDiv.appendChild(crease);

    var tagDiv=document.createElement('div');
    tagDiv.style.cssText="font-size:0.56rem;letter-spacing:0.14em;text-transform:uppercase;color:#6B5B4E;margin-top:5px;opacity:0.65;font-family:DM Sans,sans-serif";
    tagDiv.textContent=g.label;

    wrap.appendChild(hangerDiv); wrap.appendChild(photoDiv); wrap.appendChild(tagDiv);

    wrap.addEventListener('mouseenter',function(){wrap.style.transform='rotate('+(g.tilt-2)+'deg) translateY(-8px)';wrap.style.filter='drop-shadow(0 10px 18px rgba(0,0,0,0.22))';});
    wrap.addEventListener('mouseleave',function(){wrap.style.transform='rotate('+g.tilt+'deg)';wrap.style.filter='';});
    row.appendChild(wrap);
  });

  // Drag to slide along rack
  var down=false, sx=0, tx=0, cur=0;
  row.addEventListener('mousedown',function(e){down=true;sx=e.clientX;tx=cur;row.style.cursor='grabbing';});
  window.addEventListener('mouseup',function(){down=false;if(row)row.style.cursor='grab';});
  window.addEventListener('mousemove',function(e){
    if(!down)return;
    var minX=Math.min(0, panel.offsetWidth - row.scrollWidth - 20);
    cur=Math.max(minX,Math.min(0,tx+(e.clientX-sx)*0.85));
    row.style.transform='translateX('+cur+'px)';
  });
});
</script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)