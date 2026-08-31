# AgentBench

## Konumlandırma

- **Kategori:** AI / Agents
- **Zorluk:** Orta
- **Portföy amacı:** Agent orchestration, tracing ve evaluation tarafında daha ciddi sistem tasarımı gösterir.

## Amaç

Agent veya agent konfigürasyonlarını gerçek görevler üzerinde ölçülebilir şekilde karşılaştırmak.

## Çözdüğü Problem

Agent kalitesi yalnız final cevaptan ibaret değildir; tool call, retry, süre ve görev başarısı birlikte ölçülmelidir.

## MVP Kapsamı

- Agent adapter interface
- Task runner
- Tool-call event log
- Timeout/retry accounting
- Deterministic evaluator hooks
- JSON report
- CLI

## Önerilen Teknik Yığın

- Python 3.12+
- Pydantic
- Typer
- asyncio
- pytest

## Ölçülecek Metrikler

- task success
- tool calls
- retries
- wall-clock time
- token/cost
- test pass rate

## V1 Kabul Kriterleri

- Temiz bir makinede README adımlarıyla kurulabilmeli.
- Ana kullanım senaryosu tek komut veya kısa bir akışla çalışmalı.
- Kritik çekirdek davranışlar testlerle doğrulanmalı.
- Hatalı input kontrollü biçimde ele alınmalı.
- Örnek input ve örnek output repoda bulunmalı.
- GitHub Actions üzerinde temel test/lint akışı çalışmalı.
- Secret veya kişisel veri repository'ye girmemeli.

## Repo Yapısı

```text
agentbench/
├── src/
├── tests/
├── examples/
├── docs/
├── .github/
│   └── workflows/
├── README.md
├── LICENSE
├── CHANGELOG.md
└── .gitignore
```

Gereksiz klasörler sırf şablon için açılmamalı.

## İlk Milestone'lar

### M1 — Foundation
- Proje skeleton
- CLI/app entrypoint
- Config modeli
- Test altyapısı
- CI

### M2 — Core
- MVP'nin ana fonksiyonları
- Temel hata yönetimi
- Örnek veri

### M3 — Quality
- Edge-case testleri
- README
- Example output
- Release hazırlığı

### M4 — Release
- `v0.1.0`
- GitHub topics
- Açıklama ve ekran görüntüsü
- Issues için başlangıç etiketleri

## Sonraki Geliştirmeler

- sandboxed coding tasks
- trace viewer
- multi-agent comparison
- failure taxonomy
- benchmark packs

## Bilinçli Olarak Yapılmayacaklar

- İlk sürümde gereksiz SaaS/account sistemi
- Sırf "AI project" görünmesi için zorunlu LLM entegrasyonu
- Kullanılmayan mikroservisler
- Erken optimizasyon
- Gizli/local sistemlerden proprietary mantık kopyalama

## GitHub Sunumu

README ilk ekranı şu dört şeyi hızlı göstermeli:

1. Bu araç ne yapıyor?
2. Neden var?
3. 30 saniyede nasıl denenir?
4. Örnek çıktı nasıl görünüyor?

Önerilen repository topics:

`ai-agents`, `developer-tools`, `portfolio`, `open-source`

## Commit Standardı

Örnek:

```text
feat: add core runner
test: cover invalid configuration
fix: handle timeout correctly
docs: add quick-start example
chore: configure CI
```

## Tamamlanmış Sayılma Şartı

Proje, yalnız kod yazıldığı için tamamlanmış sayılmaz. Aşağıdakiler olmadan `Done` değildir:

- Çalışan MVP
- Test
- README
- Example
- CI
- Release tag
