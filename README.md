# Fourier Outline Studio

Alat tanpa dependensi untuk mengubah **outline tertutup** menjadi animasi epicycle Fourier di browser. Terinspirasi oleh [reel Nitesh Yadav](https://www.instagram.com/reel/DeQgfnhqLZL/), bukan salinan kode atau aset videonya.

## Pakai

```bash
python3 fourier_outline.py example.csv -o demo.html
# buka demo.html di browser
python3 -m unittest -v
```

Input: CSV `x,y` satu titik per baris, atau SVG berisi **tepat satu** `polygon`/`polyline` dengan atribut `points`. Outline otomatis ditutup; SVG `<path>`, lubang, dan multi-kontur belum didukung. Ekspor SVG hasil rekonstruksi dari tombol di browser.

```bash
python3 fourier_outline.py outline.svg -o hasil.html --samples 512 --harmonics 120 --error 0.005
```

`--error` menargetkan *relative RMS* pada sampel kontur, **bukan** galat maksimum pada tiap titik. Resampling berdasarkan panjang busur mencegah kepadatan titik yang tak seragam mendominasi hasil; harmonik positif/negatif dihitung dengan DFT diskret dan dipilih berdasarkan energi hingga ambang galat tercapai atau batas frekuensi habis. Angka galat dicetak dan disematkan ke HTML. Akurasi bentuk sudut tajam memerlukan lebih banyak harmonik. Kompleksitas pra-hitung O(samples × harmonics), dibatasi 2048 sampel agar tetap ringan.

File HTML bersifat mandiri dan berjalan offline; tidak mengirim gambar atau koordinat ke layanan luar. Karya ini tidak mengklaim galat atau bentuk kuda dari reel karena outline aslinya tidak tersedia.

© Bagas Cihuy. MIT License.
