# AgentBench — Agent Roadmap

## Amaç

V1'i küçük, test edilebilir milestone'lara bölerek geliştirmek.

## M1 — Foundation

Agent görevleri:

1. Proje skeleton oluştur.
2. Dependency yönetimini kur.
3. Config modellerini oluştur.
4. CLI/app entrypoint ekle.
5. Test altyapısını kur.
6. GitHub Actions workflow ekle.

Çıkış kriteri:

- Uygulama başlıyor.
- En az bir smoke test geçiyor.
- CI config mevcut.

## M2 — Core Implementation

Uygulanacak V1 kapsamı:

- Agent adapter interface
- Task runner
- Tool-call event log
- Timeout/retry accounting
- Deterministic evaluator hooks
- JSON report
- CLI

Kurallar:

- Her büyük feature için test.
- IO ve core logic ayrılmalı.
- Hatalar typed/structured ele alınmalı.
- Gereksiz abstraction eklenmemeli.

## M3 — Hardening

- Invalid input testleri
- Timeout/error path
- Deterministic fixture'lar
- Logging
- Example dataset/input
- Performance sanity check

## M4 — Documentation

- README quick start
- Installation
- Usage
- Example output
- Architecture özeti
- Limitations
- Roadmap

## M5 — Release Candidate

- Tüm testleri çalıştır.
- Lint/type-check varsa çalıştır.
- Secret scan yap.
- Changelog oluştur.
- `0.1.0` release candidate raporu üret.

## Agent'ın Yapmaması Gerekenler

- Yeni ürün özelliği icat etmek
- İnsan onayı olmadan V2'ye geçmek
- Proprietary/local sistem kodu taşımak
- Gerçek credential commit etmek
- Testleri atlayarak "done" ilan etmek
