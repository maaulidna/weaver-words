from flask import Flask, render_template, request, jsonify
import random
import json
from groq import Groq

app = Flask(__name__)

client = Groq(api_key='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')


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
    return jsonify({'kata': kata, 'tingkat': tingkat})

@app.route('/nilai', methods=['POST'])
def nilai():
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
1. Koherensi dan Kohesi (0-25): kelogisan alur antarkalimat, keterkaitan antarbagian
2. Kreativitas dan Integrasi Kata (0-30): seberapa natural dan kreatif kata acak digunakan
3. Kebahasaan (0-25): tata bahasa, ejaan EYD, kekayaan kalimat
4. Ketepatan Penggunaan Kata Acak (0-20): apakah semua kata digunakan secara kontekstual

Berikan respons HANYA dalam format JSON berikut, tanpa teks lain:
{{
  "skor_koherensi": <angka 0-25>,
  "skor_kreativitas": <angka 0-30>,
  "skor_kebahasaan": <angka 0-25>,
  "skor_penggunaan_kata": <angka 0-20>,
  "skor_total": <jumlah keempat skor>,
  "feedback": "<feedback naratif 3-4 kalimat dalam bahasa Indonesia>"
}}"""

    try:
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.2
)
        teks = response.choices[0].message.content.strip()
        if teks.startswith('```'):
            teks = teks.split('```')[1]
            if teks.startswith('json'):
                teks = teks[4:]
        hasil = json.loads(teks)
        return jsonify({
            'skor': hasil['skor_total'],
            'feedback': f"Koherensi: {hasil['skor_koherensi']}/25 | Kreativitas: {hasil['skor_kreativitas']}/30 | Kebahasaan: {hasil['skor_kebahasaan']}/25 | Penggunaan Kata: {hasil['skor_penggunaan_kata']}/20\n\n{hasil['feedback']}"
        })
    except Exception as e:
        return jsonify({'skor': 0, 'feedback': f'Error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)