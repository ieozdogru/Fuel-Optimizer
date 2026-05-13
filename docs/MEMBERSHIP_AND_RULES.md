# Üyelik Fonksiyonları ve Kural Tabanı (Fuel Optimizer)

Bu doküman, projede kullanılan **üyelik fonksiyonlarının nasıl belirlendiğini** ve denetleyicinin kullandığı **16 adet kural tabanını** rapor/presentasyon için “tek yerde” toplar.

Kaynak kod referansı: `fuzzy_engine.py` (üyelik fonksiyonları + kurallar), `engine_configs.py` (motor profili parametreleri).

---

## 1) Girdiler, çıktı ve evrenler

Denetleyici 3 girdi (antecedent) ve 1 çıktı (consequent) ile çalışır:

- **Devir (RPM)**: [0, rpmmax], adım 1 RPM
- **Gaz (%)**: [0, 100], adım 1
- **Eğim (°)**: [-20, 20], adım 1
- **Çıktı “asistan_karari” skoru**: [0, 100], adım 1

> Her araç profili için devir evreninin üst sınırı `rpm_max` ile belirlenir. Bu nedenle devir üyelik fonksiyonları **profil bazlı ölçeklenir**.

---

## 2) Motor profili parametreleri (devir ölçekleme)

Her araç profili `engine_configs.py` içinde şu üç parametre ile tanımlıdır:

- `**rpm_max`**: motorun maksimum devri (evren üst sınırı)
- `**ideal_range = [ideal_min, ideal_max]**`: verimli/ekonomik sürüş bandı
- `**high_rev**`: “yüksek devir” bölgesine geçiş eşiği (redline öncesi)

Örnek profiller:

- Fiat Linea 1.3 Multijet (Dizel): `rpm_max=5000`, `ideal=1750–2500`, `high_rev=3500`
- Toyota Corolla 1.6 (Benzinli): `rpm_max=7000`, `ideal=2500–4000`, `high_rev=5000`
- VW Golf 1.0 TSI (Turbo Benzin): `rpm_max=6000`, `ideal=2000–3500`, `high_rev=4500`

---

## 3) Üyelik fonksiyonları nasıl belirleniyor?

Üyelik fonksiyonları **3 giriş + 1 çıktı** için tanımlanır. Fonksiyon tipleri: üçgensel `trimf([a,b,c])` ve trapez `trapmf([a,b,c,d])`.

- **Devir (RPM)**: profil bazlı ölçeklenir. Parametreler: `rpm_max`, `ideal_min`, `ideal_max`, `high_rev`, `ideal_mid=(ideal_min+ideal_max)/2`.
  - Düşük: `trimf([0, 0, ideal_min+100])`
  - İdeal: `trimf([ideal_min-200, ideal_mid, ideal_max+200])`
  - Yüksek: `trapmf([ideal_max, high_rev, rpm_max, rpm_max])`
- **Gaz (%)**:
  - Az: `trimf([0, 0, 30])` · Orta: `trimf([20, 50, 80])` · Tam_Gaz: `trimf([70, 100, 100])`
- **Eğim (°)**:
  - Yokus_Asagi: `trimf([-20, -20, -5])` · Duz: `trimf([-10, 0, 10])` · Yokus_Yukari: `trimf([5, 20, 20])`
- **Çıktı skoru (0–100)**:
  - Vites_Kucult: `trimf([0, 0, 30])`
  - Gazdan_Cek: `trimf([20, 35, 50])`
  - Durumu_Koru: `trimf([40, 55, 70])`
  - Vites_Buyut: `trimf([60, 100, 100])`

**Özet:** Durulaştırma sonrası elde edilen skorun bu 4 çıktı kümesine üyelikleri hesaplanır ve **en yüksek üyeliğe sahip sınıf** tavsiye olarak seçilir.

---

## 4) Kural tabanı (16 kural)

Kural yapısı: **IF (Devir × Gaz × Eğim) THEN (Tavsiye)**.

Kısaltmalar:

- Devir: Düşük / İdeal / Yüksek
- Gaz: Az / Orta / Tam_Gaz
- Eğim: Yokus_Asagi / Duz / Yokus_Yukari


| Kural | IF (Devir, Gaz, Eğim)           | THEN (Çıktı) | Etiket                    |
| ----- | ------------------------------- | ------------ | ------------------------- |
| 1     | İdeal ∧ Orta ∧ Duz              | Durumu_Koru  | R01_flat_ideal_moderate   |
| 2     | Yüksek ∧ Orta ∧ Duz             | Vites_Buyut  | R02_flat_high_moderate    |
| 3     | Yüksek ∧ Az ∧ Duz               | Vites_Buyut  | R03_flat_high_light       |
| 4     | İdeal ∧ Az ∧ Duz                | Durumu_Koru  | R04_flat_ideal_light      |
| 5     | Düşük ∧ Orta ∧ Duz              | Vites_Kucult | R05_flat_low_moderate     |
| 6     | İdeal ∧ Tam_Gaz ∧ Duz           | Vites_Kucult | R06_flat_ideal_full       |
| 7     | Düşük ∧ Tam_Gaz ∧ Duz           | Vites_Kucult | R07_flat_low_full         |
| 8     | Düşük ∧ Yokus_Yukari            | Vites_Kucult | R08_uphill_low            |
| 9     | İdeal ∧ Tam_Gaz ∧ Yokus_Yukari  | Vites_Kucult | R09_uphill_ideal_full     |
| 10    | İdeal ∧ Orta ∧ Yokus_Yukari     | Durumu_Koru  | R10_uphill_ideal_moderate |
| 11    | Yüksek ∧ Tam_Gaz ∧ Yokus_Yukari | Durumu_Koru  | R11_uphill_high_full      |
| 12    | Yüksek ∧ Orta ∧ Yokus_Yukari    | Durumu_Koru  | R12_uphill_high_moderate  |
| 13    | İdeal ∧ Yokus_Asagi             | Gazdan_Cek   | R13_downhill_ideal        |
| 14    | Yüksek ∧ Az ∧ Yokus_Asagi       | Gazdan_Cek   | R14_downhill_high_light   |
| 15    | Düşük ∧ Az ∧ Yokus_Asagi        | Durumu_Koru  | R15_downhill_low_light    |
| 16    | Düşük ∧ Orta ∧ Yokus_Asagi      | Vites_Buyut  | R16_downhill_low_moderate |


**Not:** Bazı kurallar (8, 13) iki terimle yazılmıştır: ör. “Düşük ∧ Yokuş Yukarı”. Bu, ilgili senaryoda gazdan bağımsız bir güvenlik/performans kararını temsil eder.

---

## 5) Mamdani vs Sugeno

- **Mamdani**: min ile AND, max ile birleştirme, **centroid** ile durulaştırma.
- **Sugeno (0. derece)**: aynı IF kısmı; THEN tarafında her çıktı terimi bir **singleton** sayıya eşlenir ve
  \[
  y = \frac{\sum_i w_i s_i}{\sum_i w_i}
  \]
  ile ağırlıklı ortalama alınır. \(w_i\) kural ateşleme gücü, \(s_i\) singleton’dır.

