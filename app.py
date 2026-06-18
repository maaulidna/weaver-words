from flask import Flask, render_template, request, jsonify, send_from_directory
import random
import json
import os
import sqlite3
import uuid
import base64
from groq import Groq

# Memuat file .env jika ada (sangat berguna untuk development lokal)
if os.path.exists('.env'):
    with open('.env', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('shares.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS shares (
            id TEXT PRIMARY KEY,
            kata TEXT,
            esai TEXT,
            skor TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

KATA = {
    'mudah': [
        ['piring', 'sendok', 'sepeda', 'buku', 'kucing', 'garpu'],
        ['rumah', 'air', 'makan', 'jalan', 'pohon', 'tidur'],
        ['buku', 'hujan', 'langit', 'tangan', 'suara', 'angin'],
        ['meja', 'kursi', 'pintu', 'lampu', 'bunga', 'sungai'],
    ],
    'sedang': [
        ['badai', 'kacamata', 'lumpur', 'helikopter', 'kamus', 'sungai'],
        ['cermin', 'gunung', 'anggur', 'perahu', 'awan', 'mercusuar'],
        ['teleskop', 'kawanan', 'labirin', 'kompas', 'fosil', 'kanvas'],
    ],
    'sulit': [
        ['entropi', 'kamuflase', 'sinestesia', 'arketipe', 'paradigma', 'gerhana'],
        ['eklektik', 'resonansi', 'absurditas', 'simbiosis', 'katarsis', 'euforia'],
        ['metafizika', 'nihilisme', 'dialektika', 'epistemologi', 'fenomenologi', 'ontologi'],
    ]
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.png', mimetype='image/png')

@app.route('/kata-acak', methods=['GET'])
def kata_acak():
    tingkat = request.args.get('tingkat', 'mudah')
    daftar = KATA.get(tingkat, KATA['mudah'])
    kata_full = random.choice(daftar)
    # Sample exactly 6 words (or min of 6 and length)
    kata = random.sample(kata_full, min(6, len(kata_full)))
    return jsonify({
        'kata': [k.capitalize() for k in kata],
        'tingkat': tingkat
    })

@app.route('/nilai', methods=['POST'])
def nilai():
    try:
        data = request.get_json()
        esai = data.get('esai', '')
        kata = data.get('kata', [])
        kata_str = ', '.join(kata)

        prompt = f"""Kamu adalah penilai esai profesional berbahasa Indonesia.

Tugas pengguna: merangkai kata-kata acak berikut menjadi sebuah esai atau paragraf yang padu.
Kata acak yang diberikan: {kata_str}

Esai yang ditulis pengguna:
\"\"\"{esai}\"\"\"

Nilai esai ini berdasarkan 4 dimensi berikut:
1. Koherensi (0-25): Mengukur perpaduan dan kelancaran alur paragraf.
2. Kebahasaan (0-25): Mengukur kesesuaian tata bahasa, ejaan, tanda baca, dan efektivitas kalimat.
3. Kreativitas (0-30): Mengukur keunikan ide, cara menghubungkan kata, dan gaya bercerita.
4. Penggunaan Kata (0-20): Mengukur ketepatan pemakaian kata-kata acak yang ditentukan dalam konteks kalimat. Kata-kata tersebut diperbolehkan menggunakan imbuhan bahasa Indonesia (awalan/akhiran/sisipan/gabungan, misalnya jika kata dasarnya "sepeda", maka kata "bersepeda", "sepedanya", dll. tetap dianggap terpakai secara sah).

Berikan respons HANYA dalam format JSON dengan skema objek berikut (tanpa markdown code block, tanpa penjelasan tambahan):
{{
  "koherensi": {{
    "skor": 0,
    "max_skor": 25,
    "feedback": "Penjelasan singkat mengenai koherensi...",
    "tips": "Tips taktis dan contoh konkret/bagus untuk meningkatkan koherensi esai ini."
  }},
  "kebahasaan": {{
    "skor": 0,
    "max_skor": 25,
    "feedback": "Penjelasan singkat mengenai kebahasaan...",
    "tips": "Tips taktis dan contoh konkret/bagus untuk memperbaiki ejaan atau tata bahasa esai ini."
  }},
  "kreativitas": {{
    "skor": 0,
    "max_skor": 30,
    "feedback": "Penjelasan singkat mengenai kreativitas...",
    "tips": "Tips taktis dan contoh konkret/bagus untuk mengembangkan ide/cerita agar lebih kreatif."
  }},
  "penggunaan_kata": {{
    "skor": 0,
    "max_skor": 20,
    "feedback": "Penjelasan singkat mengenai ketepatan penggunaan kata...",
    "tips": "Tips taktis dan contoh konkret/bagus cara menyisipkan kata acak dengan lebih halus."
  }},
  "skor_total": 0,
  "feedback_umum": "Ulasan singkat keseluruhan..."
}}"""

        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[
                {'role': 'user', 'content': prompt}
            ],
            temperature=0.2
        )

        teks = response.choices[0].message.content.strip()

        if teks.startswith('```'):
            teks = teks.replace('```json', '').replace('```', '').strip()

        hasil = json.loads(teks)

        # Validate structure and enforce standard ranges
        def parse_dim(key, max_val):
            dim = hasil.get(key, {})
            if not isinstance(dim, dict):
                dim = {}
            score = dim.get('skor', 0)
            try:
                score = int(score)
            except:
                score = 0
            # clamp score between 0 and max_val
            score = max(0, min(max_val, score))
            return {
                'skor': score,
                'max_skor': max_val,
                'feedback': dim.get('feedback', 'Evaluasi selesai.'),
                'tips': dim.get('tips', 'Posisikan kalimat secara logis dan pastikan transisi antar paragraf halus.')
            }

        koherensi = parse_dim('koherensi', 25)
        kebahasaan = parse_dim('kebahasaan', 25)
        kreativitas = parse_dim('kreativitas', 30)
        penggunaan_kata = parse_dim('penggunaan_kata', 20)

        # calculate total score as sum of scores
        total_skor = koherensi['skor'] + kebahasaan['skor'] + kreativitas['skor'] + penggunaan_kata['skor']

        return jsonify({
            'status': 'success',
            'koherensi': koherensi,
            'kebahasaan': kebahasaan,
            'kreativitas': kreativitas,
            'penggunaan_kata': penggunaan_kata,
            'skor_total': total_skor,
            'feedback_umum': hasil.get('feedback_umum', 'Penilaian selesai.')
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/upload-share', methods=['POST'])
def upload_share():
    try:
        data = request.get_json()
        share_id = str(uuid.uuid4())[:8]
        
        # Save image to disk
        image_data = data.get('image', '')
        if image_data.startswith('data:image/png;base64,'):
            image_data = image_data.replace('data:image/png;base64,', '')
        
        image_bytes = base64.b64decode(image_data)
        
        # Ensure static/shares directory exists
        shares_dir = os.path.join(app.root_path, 'static', 'shares')
        if not os.path.exists(shares_dir):
            os.makedirs(shares_dir)
            
        image_path = os.path.join(shares_dir, f"{share_id}.png")
        with open(image_path, "wb") as f:
            f.write(image_bytes)
            
        # Save data to DB
        kata = json.dumps(data.get('kata', []))
        esai = data.get('esai', '')
        skor = json.dumps(data.get('skor', {}))
        
        conn = sqlite3.connect('shares.db')
        c = conn.cursor()
        c.execute("INSERT INTO shares (id, kata, esai, skor) VALUES (?, ?, ?, ?)",
                  (share_id, kata, esai, skor))
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success', 'id': share_id})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/share/<share_id>')
def view_share(share_id):
    conn = sqlite3.connect('shares.db')
    c = conn.cursor()
    c.execute("SELECT kata, esai, skor FROM shares WHERE id = ?", (share_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        kata = json.loads(row[0])
        esai = row[1]
        skor = json.loads(row[2])
        image_url = f"/static/shares/{share_id}.png"
        
        # Construct full URL for OG tags
        host_url = request.host_url.rstrip('/')
        full_image_url = f"{host_url}{image_url}"
        share_url = f"{host_url}/share/{share_id}"
        
        return render_template('share.html', 
                               share_id=share_id, 
                               kata=kata, 
                               esai=esai, 
                               skor=skor, 
                               image_url=image_url,
                               full_image_url=full_image_url,
                               share_url=share_url)
    else:
        return "Share not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)