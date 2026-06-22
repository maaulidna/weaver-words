from flask import Flask, render_template, request, jsonify, send_from_directory
import random
import json
import os
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

KATA_EN = {
    'mudah': [
        ['plate', 'spoon', 'bicycle', 'book', 'cat', 'fork'],
        ['house', 'water', 'eat', 'road', 'tree', 'sleep'],
        ['book', 'rain', 'sky', 'hand', 'voice', 'wind'],
        ['table', 'chair', 'door', 'lamp', 'flower', 'river'],
    ],
    'sedang': [
        ['storm', 'glasses', 'mud', 'helicopter', 'dictionary', 'river'],
        ['mirror', 'mountain', 'grapes', 'boat', 'cloud', 'lighthouse'],
        ['telescope', 'herd', 'maze', 'compass', 'fossil', 'canvas'],
    ],
    'sulit': [
        ['entropy', 'camouflage', 'synesthesia', 'archetype', 'paradigm', 'eclipse'],
        ['eclectic', 'resonance', 'absurdity', 'simbiosis', 'catharsis', 'euphoria'],
        ['metaphysics', 'nihilism', 'dialectics', 'epistemology', 'phenomenology', 'ontology'],
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
    lang = request.args.get('lang', 'id')
    jumlah = int(request.args.get('jumlah', 6))
    jumlah = max(3, min(10, jumlah))

    daftar = KATA_EN.get(tingkat, KATA_EN['mudah']) if lang == 'en' else KATA.get(tingkat, KATA['mudah'])
    
    if jumlah <= 6:
        # Ambil 1 baris kata secara acak
        kata_full = random.choice(daftar)
        kata = random.sample(kata_full, min(jumlah, len(kata_full)))
    else:
        # Gabungkan semua kata dalam tingkat kesulitan tersebut agar cukup
        flat_list = list(set([word for sublist in daftar for word in sublist]))
        kata = random.sample(flat_list, min(jumlah, len(flat_list)))

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
        lang = data.get('lang', 'id')
        tema = data.get('tema', 'bebas')
        kata_str = ', '.join(kata)

        tema_map = {
            'id': {
                'bebas': 'Bebas',
                'filosofis': 'Filosofis (Filsafat)',
                'fiksi_ilmiah': 'Fiksi Ilmiah (Science Fiction)',
                'misteri': 'Misteri / Detektif',
                'romantis': 'Romantis (Percintaan)'
            },
            'en': {
                'bebas': 'Free Theme / General',
                'filosofis': 'Philosophical',
                'fiksi_ilmiah': 'Science Fiction',
                'misteri': 'Mystery / Detective',
                'romantis': 'Romance / Drama'
            }
        }
        
        tema_display_id = tema_map['id'].get(tema, 'Bebas')
        tema_display_en = tema_map['en'].get(tema, 'Free Theme / General')

        if lang == 'en':
            prompt = f"""You are a professional essay evaluator.
            
            Task: Weave these random words into a cohesive paragraph based on the specified writing theme.
            Random words provided: {kata_str}
            Writing Theme: {tema_display_en}
            
            Essay written by user:
            \"\"\"{esai}\"\"\"
            
            Grade this essay based on these 4 dimensions:
            1. Coherence (0-25): Measures connection and paragraph flow.
            2. Grammar & Language (0-25): Measures grammatical accuracy, spelling, punctuation, and sentence effectiveness.
            3. Creativity (0-30): Measures uniqueness of ideas, word connections, storytelling style, and how well the essay follows the selected theme '{tema_display_en}'.
            4. Word Usage (0-20): Measures accuracy of using the given random words. English affixes/inflections (e.g. "bicycles", "bicycling", "cycled" for "bicycle") are allowed.
            
            CRITICAL REQUIREMENT: Since the essay is written in English and the user requested the English interface, your entire evaluation and all text values inside the JSON object (specifically "feedback", "tips", and "feedback_umum") MUST be written strictly in English. Do NOT write in Indonesian or use Indonesian phrases in the text values.
            
            Return ONLY a JSON response matching the following schema (no markdown, no extra explanation):
            {{
              "koherensi": {{
                "skor": 0,
                "max_skor": 25,
                "feedback": "Brief feedback about coherence in English...",
                "tips": "Tactical tips and good examples to improve coherence in English."
              }},
              "kebahasaan": {{
                "skor": 0,
                "max_skor": 25,
                "feedback": "Brief feedback about grammar in English...",
                "tips": "Tactical tips and good examples to fix grammar/spelling in English."
              }},
              "kreativitas": {{
                "skor": 0,
                "max_skor": 30,
                "feedback": "Brief feedback about creativity in English...",
                "tips": "Tactical tips and good examples to make it more creative in English."
              }},
              "penggunaan_kata": {{
                "skor": 0,
                "max_skor": 20,
                "feedback": "Brief feedback about word usage in English...",
                "tips": "Tactical tips and good examples to integrate words more smoothly in English."
              }},
              "skor_total": 0,
              "feedback_umum": "Overall summary feedback in English..."
            }}"""
        else:
            prompt = f"""Kamu adalah penilai esai profesional berbahasa Indonesia.
            
            Tugas pengguna: merangkai kata-kata acak berikut menjadi sebuah esai atau paragraf yang padu sesuai dengan tema penulisan yang dipilih.
            Kata acak yang diberikan: {kata_str}
            Tema Penulisan: {tema_display_id}
            
            Esai yang ditulis pengguna:
            \"\"\"{esai}\"\"\"
            
            Nilai esai ini berdasarkan 4 dimensi berikut:
            1. Koherensi (0-25): Mengukur perpaduan dan kelancaran alur paragraf.
            2. Kebahasaan (0-25): Mengukur kesesuaian tata bahasa, ejaan, tanda baca, dan efektivitas kalimat.
            3. Kreativitas (0-30): Mengukur keunikan ide, cara menghubungkan kata, gaya bercerita, serta seberapa baik esai mengikuti tema penulisan '{tema_display_id}' yang dipilih.
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
                'feedback': dim.get('feedback', 'Evaluasi selesai.' if lang == 'id' else 'Evaluation completed.'),
                'tips': dim.get('tips', 'Posisikan kalimat secara logis.' if lang == 'id' else 'Structure sentences logically.')
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
            'feedback_umum': hasil.get('feedback_umum', 'Penilaian selesai.' if lang == 'id' else 'Evaluation completed.')
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)