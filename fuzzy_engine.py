import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class FuzzyEngine:
    def __init__(self, config):
        """
        Gelen Araç Config profiline göre Sınıf (Class) başlatılır.
        Bu sayede Fuzzy Engine, tamamen parametrik (dinamik) çalışır.
        """
        self.config = config
        self.rpm_max = config['rpm_max']
        self.ideal_min, self.ideal_max = config['ideal_range']
        self.high_rev = config['high_rev']
        
        self._build_engine()

    def _build_engine(self):
        """
        Bulanık Mantık (Fuzzy Logic) kontrol sistemini kurgular ve döner.
        Üyelik fonksiyonları artık dinamik olarak girilen limite (self.rpm_max) göre şekillenir.
        """
        # 1. GİRDİLER VE ÇIKTI
        devir = ctrl.Antecedent(np.arange(0, self.rpm_max + 1, 1), 'devir')
        gaz = ctrl.Antecedent(np.arange(0, 101, 1), 'gaz')
        egim = ctrl.Antecedent(np.arange(-20, 21, 1), 'egim')
        
        karar = ctrl.Consequent(np.arange(0, 101, 1), 'asistan_karari')
        
        # 2. ÜYELİK FONKSİYONLARI (MEMBERSHIP FUNCTIONS) - DİNAMİK YAPILANDIRMA
        # Düşük devir başlangıçtan idea'le kadar uzanır
        devir['Düşük'] = fuzz.trimf(devir.universe, [0, 0, self.ideal_min + 100])
        
        # İdeal devir min ve max ortalanacak şekilde belirlenir
        ideal_mid = (self.ideal_min + self.ideal_max) / 2
        devir['İdeal'] = fuzz.trimf(devir.universe, [self.ideal_min - 200, ideal_mid, self.ideal_max + 200])
        
        # Yüksek devir, ideal_max barajından High_Rev aşıp redline'a (rpm_max) kadar gider
        devir['Yüksek'] = fuzz.trapmf(devir.universe, [self.ideal_max, self.high_rev, self.rpm_max, self.rpm_max])
        
        gaz['Az'] = fuzz.trimf(gaz.universe, [0, 0, 30])
        gaz['Orta'] = fuzz.trimf(gaz.universe, [20, 50, 80])
        gaz['Tam_Gaz'] = fuzz.trimf(gaz.universe, [70, 100, 100])
        
        egim['Yokus_Asagi'] = fuzz.trimf(egim.universe, [-20, -20, -5])
        egim['Duz'] = fuzz.trimf(egim.universe, [-10, 0, 10])
        egim['Yokus_Yukari'] = fuzz.trimf(egim.universe, [5, 20, 20])
        
        karar['Vites_Kucult'] = fuzz.trimf(karar.universe, [0, 0, 30])
        karar['Gazdan_Cek'] = fuzz.trimf(karar.universe, [20, 35, 50])
        karar['Durumu_Koru'] = fuzz.trimf(karar.universe, [40, 55, 70])
        karar['Vites_Buyut'] = fuzz.trimf(karar.universe, [60, 100, 100])

        # 3. KURAL TABANI (RULE BASE)
        # Evrensel (Universal) kurallar. Üyelik fonksiyonları dinamik olduğu için bu kurallar her araca adapte olur.
        rules = [
            # Düz Yol (Normal Sürüş) Senaryoları
            ctrl.Rule(devir['İdeal'] & gaz['Orta'] & egim['Duz'], karar['Durumu_Koru']),
            ctrl.Rule(devir['Yüksek'] & gaz['Orta'] & egim['Duz'], karar['Vites_Buyut']),
            ctrl.Rule(devir['Yüksek'] & gaz['Az'] & egim['Duz'], karar['Vites_Buyut']),
            ctrl.Rule(devir['İdeal'] & gaz['Az'] & egim['Duz'], karar['Durumu_Koru']),
            ctrl.Rule(devir['Düşük'] & gaz['Orta'] & egim['Duz'], karar['Vites_Kucult']),
            ctrl.Rule(devir['İdeal'] & gaz['Tam_Gaz'] & egim['Duz'], karar['Vites_Kucult']),
            ctrl.Rule(devir['Düşük'] & gaz['Tam_Gaz'] & egim['Duz'], karar['Vites_Kucult']),
            
            # Yokuş Yukarı (Tırmanma) Senaryoları
            ctrl.Rule(devir['Düşük'] & egim['Yokus_Yukari'], karar['Vites_Kucult']),
            ctrl.Rule(devir['İdeal'] & gaz['Tam_Gaz'] & egim['Yokus_Yukari'], karar['Vites_Kucult']), 
            ctrl.Rule(devir['İdeal'] & gaz['Orta'] & egim['Yokus_Yukari'], karar['Durumu_Koru']),
            ctrl.Rule(devir['Yüksek'] & gaz['Tam_Gaz'] & egim['Yokus_Yukari'], karar['Durumu_Koru']), 
            ctrl.Rule(devir['Yüksek'] & gaz['Orta'] & egim['Yokus_Yukari'], karar['Durumu_Koru']),
            
            # Yokuş Aşağı (İniş / Motor Freni) Senaryoları
            ctrl.Rule(devir['İdeal'] & egim['Yokus_Asagi'], karar['Gazdan_Cek']), 
            ctrl.Rule(devir['Yüksek'] & gaz['Az'] & egim['Yokus_Asagi'], karar['Gazdan_Cek']),
            ctrl.Rule(devir['Düşük'] & gaz['Az'] & egim['Yokus_Asagi'], karar['Durumu_Koru']),
            ctrl.Rule(devir['Düşük'] & gaz['Orta'] & egim['Yokus_Asagi'], karar['Vites_Buyut']) 
        ]
        
        # Obje dışından erişim için kaydet
        self.karar_degiskeni = karar
        karar_ctrl = ctrl.ControlSystem(rules)
        self.sim = ctrl.ControlSystemSimulation(karar_ctrl)
        
    def evaluate(self, devir_val, gaz_val, egim_val):
        """
        Verilen Telemetri verilerini sisteme hesaplatır ve en uygun Çözümü / Skoru sözlük formatında döner.
        """
        self.sim.input['devir'] = devir_val
        self.sim.input['gaz'] = gaz_val
        self.sim.input['egim'] = egim_val
        
        try:
            self.sim.compute()
            skor = self.sim.output['asistan_karari']
            
            # Defuzzification derecelerinden en baskın önerinin çekilmesi
            uyelik_dereceleri = {
                'VİTES KÜÇÜLT': fuzz.interp_membership(self.karar_degiskeni.universe, self.karar_degiskeni['Vites_Kucult'].mf, skor),
                'GAZDAN ÇEK': fuzz.interp_membership(self.karar_degiskeni.universe, self.karar_degiskeni['Gazdan_Cek'].mf, skor),
                'DURUMU KORU': fuzz.interp_membership(self.karar_degiskeni.universe, self.karar_degiskeni['Durumu_Koru'].mf, skor),
                'VİTES BÜYÜT': fuzz.interp_membership(self.karar_degiskeni.universe, self.karar_degiskeni['Vites_Buyut'].mf, skor)
            }
            en_iyi_tavsiye = max(uyelik_dereceleri, key=uyelik_dereceleri.get)
            
            return {'skor': skor, 'tavsiye': en_iyi_tavsiye, 'success': True}
            
        except KeyError:
            return {'skor': 50, 'tavsiye': 'DURUMU KORU', 'success': False, 'hata': 'KeyError'}
        except ValueError:
            return {'skor': 50, 'tavsiye': 'DURUMU KORU', 'success': False, 'hata': 'ValueError'}

    def plot_result(self, skor):
        """
        Matplotlib GUI Crash uyarılarını (Streamlit'te sıklıkla olan UserWarning) önlemek 
        ve tamamen stabil bir grafik çıkarmak için manuel çizim (güvenli) yöntemi kullanılmıştır.
        """
        plt.close('all')
        fig, ax = plt.subplots(figsize=(10, 3.5))
        x_karar = self.karar_degiskeni.universe
        
        ax.plot(x_karar, self.karar_degiskeni['Vites_Kucult'].mf, 'b', label='Vites Küçült')
        ax.plot(x_karar, self.karar_degiskeni['Gazdan_Cek'].mf, 'g', label='Gazdan Çek')
        ax.plot(x_karar, self.karar_degiskeni['Durumu_Koru'].mf, 'y', label='Durumu Koru')
        ax.plot(x_karar, self.karar_degiskeni['Vites_Buyut'].mf, 'r', label='Vites Büyüt')
        
        ax.axvline(x=skor, color='k', linestyle='--', linewidth=3, label=f'Hesaplanan Skor: {skor:.1f}')
        ax.set_xlabel("Karar Skoru")
        ax.set_ylabel("Üyelik Derecesi")
        ax.legend()
        ax.grid(True, alpha=0.3)
        return fig
