# Changelog

<!-- sprint-flow:changelog — i giorni li scrive ogni notte il timer di sprint-flow
     (proxmox_doctor, deploy/sprint-flow) dai commit: non modificarli a mano. -->

Cosa è cambiato, giorno per giorno, e chi l'ha fatto. Ogni argomento indica gli
agenti che hanno fatto i commit (trailer `Agent:`); «Dal backlog» elenca le voci
tolte da `BACKLOG.md` perché fatte. Il file parte dal 2026-11-13: per la storia
precedente valgono `git log` e le note delle release.

<!-- sprint-flow:inizio f8de61179a3e3e1ed23b6f892cedcae6415467f6 -->
<!-- sprint-flow:giorni -->
<!-- sprint-flow:ultimo f5e47fffe2f2bc1fc148d8cf833b5f8836b91905 -->

## 2026-11-16
<!-- sprint-flow:giorno commit=1 testo=prod-default -->

**CI semplificata e documentazione allineata** — opencode
- Il workflow CI ora gira solo su main e ha permessi di sola lettura sui contenuti.
- La documentazione CI/CD descrive la pipeline reale: unittest con Python 3.11 e uv, con paths-ignore.
- Rimossi i riferimenti al contratto dell'installer e a .agent/pipeline.yml, che non esistono più.
- Documentato che non esiste una CD.
- Aggiunta al backlog una voce sui bytecode __pycache__ versionati.

<!-- sprint-flow:giorni-fine -->
