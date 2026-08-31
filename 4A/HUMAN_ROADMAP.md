# AgentBench — Human Roadmap

Bu dosya insan tarafından verilmesi gereken kararları ve manuel doğrulamaları içerir.

## Phase 0 — Kararlar

- [ ] Repository adı ve açıklamasını kesinleştir.
- [ ] Public license seç: varsayılan öneri MIT.
- [ ] Desteklenecek minimum Python/Node sürümünü belirle.
- [ ] V1 için dış servis/API gerekiyorsa kişisel test anahtarlarını local `.env` içine koy.
- [ ] GitHub repository'yi oluştur.

## Phase 1 — Foundation QA

- [ ] Projeyi sıfırdan kur.
- [ ] `--help` veya ana entrypoint'i çalıştır.
- [ ] Test komutunu çalıştır.
- [ ] CI sonucunu kontrol et.

## Phase 2 — Core QA

- [ ] En az 3 gerçek kullanım senaryosunu elle dene.
- [ ] Hatalı config/input senaryosunu dene.
- [ ] Output'un okunabilir ve teknik olarak anlamlı olduğunu kontrol et.

## Phase 3 — Public Readiness

- [ ] README ilk 30 saniyede projeyi açıklıyor mu?
- [ ] Ekran görüntüsü / terminal output ekle.
- [ ] Secret veya local path kalmadığını kontrol et.
- [ ] LICENSE ve `.gitignore` kontrolü yap.
- [ ] Release notes hazırla.

## Phase 4 — Release

- [ ] `v0.1.0` tag/release
- [ ] GitHub topics
- [ ] Profilde pinlenmeye değer olup olmadığına karar ver.

## İnsan Onayı Gerektiren Noktalar

Agent aşağıdakileri kendiliğinden yapmamalıdır:

- Public repository oluşturma
- Gerçek API anahtarı ekleme
- License değiştirme
- Public release yayınlama
- Scope'u V1 dışına büyütme
