from flask import Flask, render_template, request, jsonify
import random
import json
import os
from groq import Groq

app = Flask(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

KATA = {
    'mudah': [
        ['rumah', 'air', 'makan', 'jalan', 'pohon', 'tidur'],
        ['buku', 'hujan', 'langit', 'tangan', 'suara', 'angin'],
        ['meja', 'kursi', 'pintu', 'lampu', 'bunga', 'sungai'],
    ],
    'menengah': [
        ['badai', 'kacamata', 'lumpur', 'helikopter', 'kamus', 'sungai'],
        ['cermin', 'gunung', 'anggur', 'perahu', 'awan', 'mercusuar'],
        ['teleskop', 'kawanan', 'labirin', 'kompas', 'fosil', 'kanvas'],
    ],
    'sulit': [
        ['entropi', 'kamuflase', 'sinestesia', 'arketipe', 'paradigma', 'gerhana'],
        ['eklektik', 'resonansi', 'absurditas', 'simbiosis', 'katarsis', 'euforia'],
        ['metafisika', 'nihilisme', 'dialektika', 'epistemologi', 'fenomenologi', 'ontologi'],
    ]
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/kata-acak', methods=['GET'])
def kata_acak():
    tingkat = request.args.get('tingkat', 'mudah')
    daftar = KATA.get(tingkat, KATA['mudah'])
    kata = random.choice(daftar)
    return jsonify({
        'kata': kata,
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
1. Koherensi dan Kohesi (0-25)
2. Kreativitas dan Integrasi Kata (0-30)
3. Kebahasaan (0-25)
4. Ketepatan Penggunaan Kata Acak (0-20)

Berikan respons HANYA dalam format JSON:
{{
  "skor_koherensi": 0,
  "skor_kreativitas": 0,
  "skor_kebahasaan": 0,
  "skor_penggunaan_kata": 0,
  "skor_total": 0,
  "feedback": "..."
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

        return jsonify({
            'skor': hasil['skor_total'],
            'feedback': (
                f"Koherensi: {hasil['skor_koherensi']}/25 | "
                f"Kreativitas: {hasil['skor_kreativitas']}/30 | "
                f"Kebahasaan: {hasil['skor_kebahasaan']}/25 | "
                f"Penggunaan Kata: {hasil['skor_penggunaan_kata']}/20\n\n"
                f"{hasil['feedback']}"
            )
        })

    except Exception as e:
        return jsonify({
            'skor': 0,
            'feedback': f'Error: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run()