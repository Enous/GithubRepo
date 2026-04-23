# 🌌 EnpaiManage (Enpai Dev)

**EnpaiManage**, GitHub repolarınızı tek tıkla organize eden, yapay zeka destekli, modern arayüzlü ve akıllı bir yönetim aracıdır.

---

## 🚀 Temel Özellikler

- **🎨 Gece Mavisi Tema & Kar Animasyonu**: CustomTkinter ile hazırlanmış, arka planında kar yağan şık ve modern "Night Blue" premium tasarım.
- **🤖 AI Kod Analizi**: Groq Cloud entegrasyonu (Llama 3.3-70B) ile indirilen repoların ne işe yaradığını saniyeler içinde Türkçe olarak analiz edin.
- **📊 Canlı GitHub İstatistikleri**: Depoların anlık Yıldız (Star), Fork, Açık Issue ve Dil bilgilerini doğrudan arayüzden görüntüleyin.
- **📂 Akıllı Kategorizasyon**: Repoları otomatik olarak AI, Web, Security, Python gibi klasörlere ayırır.
- **🔄 Canlı Senkronizasyon & Hızlı Arama**: Klasörden sildiğiniz bir dosya uygulamadan da anında silinir. İsme veya kategoriye göre anında filtreleme yapabilirsiniz.
- **📝 Profil README Oluşturucu**: Koleksiyonunuzu şık bir Markdown listesi olarak dışa aktarın ve GitHub profilinizde sergileyin.
- **💻 VS Code & Git Entegrasyonu**: Repoları tek tıkla VS Code'da açın veya `git pull` ile anında güncelleyin.
- **⚡ Tam Sürüm Uyumluluğu**: PyQt6 yerine tamamen Python tabanlı **CustomTkinter** kullanılmıştır. Python 3.14 gibi en yeni ve deneysel sürümlerde bile sorunsuz çalışır.

---

## 🛠️ Başlangıç

1.  **Kurulum**: `kurulum.bat` dosyasına sağ tıklayıp "Yönetici Olarak Çalıştır" diyerek gerekli kütüphaneleri (CustomTkinter) yükleyin.
2.  **Başlat**: `baslat.bat` ile uygulamayı açın.
3.  **Yapay Zeka Analizi**: Kodları analiz etmek için [Groq Cloud](https://console.groq.com/) üzerinden ücretsiz bir API key alıp Ayarlar kısmına yapıştırın.
4.  **Kullanım**: Repoları listelemek veya klonlamak için ilgili Github linklerini ana ekrandan yapıştırın ve indirmeyi başlatın.

---

## 🔒 Güvenlik ve Yetki
Uygulama, Windows üzerindeki kilitli klasörleri ve Git izinlerini sorunsuz yönetebilmek için otomatik olarak **Yönetici yetkisi** ister. Tüm verileriniz (GitHub Token, Groq API Key vb.) yalnızca kendi yerel bilgisayarınızda (`~/.config/enpaimanage/`) şifresiz ama güvenli bir şekilde saklanır, dışarıya aktarılmaz.

---

**Company:** [Enpai Dev](https://github.com/Enous)  
**Developer:** **Enous**  
**License:** MIT
