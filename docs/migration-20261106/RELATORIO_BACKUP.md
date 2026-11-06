# Backup e continuidade DocRisk AI — 06/11/2026

## A. Estado do repositório

Remote confirmado: https://github.com/camileile/DocRisk-AI.git. main remota observada: 753c9945e1ef7d7b160f3034982cd78864b222a4. main local e8e5e0f foi mantida; existe backup/migration-20261106/local-main com esse SHA. Não houve merge, rebase, reset, clean, exclusão, alteração funcional, mudança de variável de ambiente ou deploy executado.

Encontrados 27 worktrees de um único repositório comum, 45 branches locais iniciais, 27 dessas com commits não alcançados pelo remoto no início. Não havia stash ativo. A inspeção de objetos encontrou 67 commits sem referência (incluindo stashes antigos); todos receberam novas referências de backup, sem reescrever seus commits. A busca cobriu Documents, Desktop, Downloads, OneDrive, worktrees Codex/Claude e o scratchpad Temp/claude. Três aliases de bibliotecas Windows negaram acesso; os worktrees Git registrados foram todos inspecionados. Não afirmamos leitura irrestrita de todos os diretórios do sistema.

A lista completa de branches iniciais, bases, caminhos, status, arquivos novos e ignorados está em INVENTARIO_LOCAL_PUBLICO.json. Os detalhes privados de descoberta estão no inventário local da operação. Nenhum arquivo rastreado tinha alteração staged/unstaged. Os novos arquivos foram preservados em branches separadas sem alterar os worktrees de origem.

| Diretório | Branch/estado | HEAD | Base comum com main | Modificados/staged | Novos | Ignorados |
|---|---|---|---|---|---|---|
| C:\Users\Pichau\AppData\Local\Temp\claude\a2b3145f039cb012\c69dc545-f8d3-4ce7-bf82-7d5924e6ad86\scratchpad\wt-m2 | detached | f52b97d2cde0ce2a3bdedb41b5405fc40e28a7f7 | dcc33b9ad6a4a6dccbbd6e5fcbf02a174afb7480 | 0/0 | 0 | 0 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-AI | test/d4-09-adversarial-scenarios | 168d3ea2ba7966c7ddecdad6c9997bf39f84b421 | a1f6109c0c14574091186a9c2f23e34705224818 | 0/0 | 0 | 21825 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-dev4-adversarial | codex/d4-09-stage3-review | 5a568d6052924a387ce6f5bfba763106f9c3ae24 | 1148e76d4d550846604ab3ddb2f1602beb901982 | 0/0 | 68 | 100 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-dev4-auth | test/d4-01-pr22-integration | d55689baa98c2276750df04f53ade7ea0ba757ff | f085df4aedeecc17f6b6b55cb651204dc4693ccd | 0/0 | 0 | 93 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-dev4-backup | feat/d4-08-backup-recovery | 90852d3bdbe7304f05b9dd5d5aa6669b612b3ffd | f085df4aedeecc17f6b6b55cb651204dc4693ccd | 0/0 | 0 | 94 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-dev4-demo | test/d4-02-demo-isolation | 6a6ce6cd0c66015719e17654b7c7e6f0428c487e | f085df4aedeecc17f6b6b55cb651204dc4693ccd | 0/0 | 0 | 18312 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-dev4-ops | feat/d4-07-observability | 04eef5f98cc5f61a653469d83d4e57dcc46b47df | f085df4aedeecc17f6b6b55cb651204dc4693ccd | 0/0 | 0 | 94 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-dev4-pilot | feat/d4-06-private-pilot | 7ee31394234924175e8a058d7b0fee199462f4d1 | f085df4aedeecc17f6b6b55cb651204dc4693ccd | 0/0 | 0 | 92 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-dev4-race-baseline | detached | 1148e76d4d550846604ab3ddb2f1602beb901982 | 1148e76d4d550846604ab3ddb2f1602beb901982 | 0/0 | 2 | 49 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-dev4-reconcile | feat/d4-10-distributed-processing | 2f3d282525c7721eaa1d9b7a2755b4283d5669dc | f085df4aedeecc17f6b6b55cb651204dc4693ccd | 0/0 | 100 | 29890 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-dev4-release | chore/d4-03-release-readiness | fd97fd39b58656b45bf5b65c3a8c46353b2f24dc | f085df4aedeecc17f6b6b55cb651204dc4693ccd | 0/0 | 0 | 17786 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-dev4-review01 | codex/d4-01-review-1148 | 47c3ff998e5d92cbc624662478247a4c09e0eb34 | 1148e76d4d550846604ab3ddb2f1602beb901982 | 0/0 | 0 | 91 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-dev4-review02 | codex/d4-02-review-1148 | b81b4a0652445ac8ea35ca9a9a429b1fc40b615d | 1148e76d4d550846604ab3ddb2f1602beb901982 | 0/0 | 0 | 18315 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-dev4-review04 | codex/d4-04-review-1148 | 33d17d71742bcc5ab2b03682303b91f047afff6c | 1148e76d4d550846604ab3ddb2f1602beb901982 | 0/0 | 0 | 92 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-dev4-runtime | fix/d4-04-local-runtime | 345ff4733fb2e6ccf830666a2bf271d82c9888b7 | f085df4aedeecc17f6b6b55cb651204dc4693ccd | 0/0 | 0 | 95 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-dev4-security | chore/d4-05-dependency-security | 780d92b8a0dbf2143e1784ef4395fbea9c2d8d90 | f085df4aedeecc17f6b6b55cb651204dc4693ccd | 0/0 | 0 | 92 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-dev4-stage3-integration | codex/dev4-stage3-integration | cf9b09cefb0f9cf5d120012dd7a7f330c99569c8 | 1148e76d4d550846604ab3ddb2f1602beb901982 | 0/0 | 0 | 18370 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-reconcile38 | codex/reconcile-pr38 | 2d5c56d58ee20d782f7ac1656cf78006c5604450 | 2d5c56d58ee20d782f7ac1656cf78006c5604450 | 0/0 | 552 | 15238 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-review-drafts | codex/review-drafts | e25783ff8d0c9af6bb945b1a154d17abf5aded45 | e25783ff8d0c9af6bb945b1a154d17abf5aded45 | 0/0 | 0 | 76 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-review42 | codex/review-pr42 | a6d70067f7401f2b066eed9d87e7571c65cbd3c8 | a6d70067f7401f2b066eed9d87e7571c65cbd3c8 | 0/0 | 1 | 15784 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-review44 | codex/review-pr44 | e55ad03ab70a795428d8a0a23298a42189406e1b | e55ad03ab70a795428d8a0a23298a42189406e1b | 0/0 | 1 | 15785 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-review45 | codex/review-pr45 | 60a05a999bd41bf3ab32395334ae1a088b6b0efa | 60a05a999bd41bf3ab32395334ae1a088b6b0efa | 0/0 | 1 | 15787 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-review46 | codex/review-pr46 | 2f0b8c0f7c28134a4ac2eb77eeaf77047691f0d0 | 2f0b8c0f7c28134a4ac2eb77eeaf77047691f0d0 | 0/0 | 0 | 22617 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-review47 | codex/fix-pr47 | 98339f9f0147b97df5ed1aa77ec97dc7152f45ac | 98339f9f0147b97df5ed1aa77ec97dc7152f45ac | 0/0 | 0 | 18306 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-review49 | codex/fix-pr49 | 9421d74caeb349600439a19455e75c51290a6cec | 9421d74caeb349600439a19455e75c51290a6cec | 0/0 | 3 | 18359 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-review50 | codex/fix-pr50 | e40f151bbff9d6318f936547e61b7d84a4f557c1 | e40f151bbff9d6318f936547e61b7d84a4f557c1 | 0/0 | 0 | 18365 |
| C:\Users\Pichau\Documents\GitHub\DocRisk-verify38-lf | detached | 2d5c56d58ee20d782f7ac1656cf78006c5604450 | 2d5c56d58ee20d782f7ac1656cf78006c5604450 | 0/0 | 0 | 74 |


## B. Commits e branches preservados

122 referências de código/histórico/evidências foram conferidas diretamente no GitHub e novamente em repositório vazio baixado do remoto: 115 referências de desenvolvimento/histórico e 7 de evidências. Uma já estava sincronizada (fix/auditoria-integracao-geral); as demais foram publicadas. A branch que contém este relatório/guia é publicada depois desta fotografia e seu SHA final é indicado no recibo local e na resposta final. Nenhuma branch main foi enviada.

| Branch remota | SHA local preservado | SHA remoto conferido | Situação |
|---|---|---|---|
| backup/d4-01-20261106 | 22f294ca73c95982aa0e16aeeb285a6c763d8459 | 22f294ca73c95982aa0e16aeeb285a6c763d8459 | Publicada e verificada |
| backup/d4-02-20261106 | 185b4ae13456a23730c2eba2842c202834bfec88 | 185b4ae13456a23730c2eba2842c202834bfec88 | Publicada e verificada |
| backup/d4-03-20261106 | 96bb15c8dd8c9695ace8265a9a4e21345da4cb63 | 96bb15c8dd8c9695ace8265a9a4e21345da4cb63 | Publicada e verificada |
| backup/d4-04-20261106 | 98166a282546928ec6fc9892bd710cc63248b566 | 98166a282546928ec6fc9892bd710cc63248b566 | Publicada e verificada |
| backup/d4-05-20261106 | dcb749f48b413127cf5d877670c160f8a53c5c74 | dcb749f48b413127cf5d877670c160f8a53c5c74 | Publicada e verificada |
| backup/d4-06-20261106 | e043d751c719b8d650759edd1b5ba2d3c94b4461 | e043d751c719b8d650759edd1b5ba2d3c94b4461 | Publicada e verificada |
| backup/d4-07-20261106 | b3d186d531a07efa6077f8ba61e89d271f106bf1 | b3d186d531a07efa6077f8ba61e89d271f106bf1 | Publicada e verificada |
| backup/d4-08-20261106 | 8583c007e8be47ef81c0af80a3a17047046ad14f | 8583c007e8be47ef81c0af80a3a17047046ad14f | Publicada e verificada |
| backup/d4-09-20261106 | 1cab17334bbb69d8510a671d46069bc8af42a015 | 1cab17334bbb69d8510a671d46069bc8af42a015 | Publicada e verificada |
| backup/d4-10-20261106 | 5d09bc9a3a6ef2f589cc284bddf000ce37f6a08e | 5d09bc9a3a6ef2f589cc284bddf000ce37f6a08e | Publicada e verificada |
| backup/migration-20261106/detached-1148e76d4d55 | 1148e76d4d550846604ab3ddb2f1602beb901982 | 1148e76d4d550846604ab3ddb2f1602beb901982 | Publicada e verificada |
| backup/migration-20261106/detached-2d5c56d58ee2 | 2d5c56d58ee20d782f7ac1656cf78006c5604450 | 2d5c56d58ee20d782f7ac1656cf78006c5604450 | Publicada e verificada |
| backup/migration-20261106/detached-f52b97d2cde0 | f52b97d2cde0ce2a3bdedb41b5405fc40e28a7f7 | f52b97d2cde0ce2a3bdedb41b5405fc40e28a7f7 | Publicada e verificada |
| backup/migration-20261106/history/010a885956f5 | 010a885956f5c2efaa46eae2738519fbe01aead7 | 010a885956f5c2efaa46eae2738519fbe01aead7 | Publicada e verificada |
| backup/migration-20261106/history/02d8a7a9df1f | 02d8a7a9df1f605f6182fb47a3ef5a87ab5e53f3 | 02d8a7a9df1f605f6182fb47a3ef5a87ab5e53f3 | Publicada e verificada |
| backup/migration-20261106/history/0842e157110a | 0842e157110aaae1bbdf666af482067e0f54cf80 | 0842e157110aaae1bbdf666af482067e0f54cf80 | Publicada e verificada |
| backup/migration-20261106/history/0b0c01b16ea2 | 0b0c01b16ea29095a01de14124ec9ddac9458149 | 0b0c01b16ea29095a01de14124ec9ddac9458149 | Publicada e verificada |
| backup/migration-20261106/history/132caa0f29ef | 132caa0f29efdc49166f02102a8e916e6908d592 | 132caa0f29efdc49166f02102a8e916e6908d592 | Publicada e verificada |
| backup/migration-20261106/history/17512c5da58a | 17512c5da58aa65902595ee413bb4fc593de6353 | 17512c5da58aa65902595ee413bb4fc593de6353 | Publicada e verificada |
| backup/migration-20261106/history/19fc07bb00f0 | 19fc07bb00f0536014ef2412212dfaaa89569ed3 | 19fc07bb00f0536014ef2412212dfaaa89569ed3 | Publicada e verificada |
| backup/migration-20261106/history/1b559d1203bd | 1b559d1203bd3d822261c0ff348bc101ef08db41 | 1b559d1203bd3d822261c0ff348bc101ef08db41 | Publicada e verificada |
| backup/migration-20261106/history/220888418d4f | 220888418d4fab87dd2110a816183cf1a3906d2e | 220888418d4fab87dd2110a816183cf1a3906d2e | Publicada e verificada |
| backup/migration-20261106/history/23201740a5a1 | 23201740a5a1f6150a7ce56370288bb0fa6d0bf0 | 23201740a5a1f6150a7ce56370288bb0fa6d0bf0 | Publicada e verificada |
| backup/migration-20261106/history/253f35a1d8b7 | 253f35a1d8b709f13637da63c6aa907d53de509c | 253f35a1d8b709f13637da63c6aa907d53de509c | Publicada e verificada |
| backup/migration-20261106/history/2bb5b4ba9420 | 2bb5b4ba94208dbc8079f2d9124a88218cc49ae2 | 2bb5b4ba94208dbc8079f2d9124a88218cc49ae2 | Publicada e verificada |
| backup/migration-20261106/history/2bc77b673ab1 | 2bc77b673ab17071b9432bc72ba6c60fe90460a9 | 2bc77b673ab17071b9432bc72ba6c60fe90460a9 | Publicada e verificada |
| backup/migration-20261106/history/2bfa0401594a | 2bfa0401594ae26b3301487292068e2740f17e34 | 2bfa0401594ae26b3301487292068e2740f17e34 | Publicada e verificada |
| backup/migration-20261106/history/3c0129c5b6b1 | 3c0129c5b6b1182eecee6ab92a57355b92cd0d58 | 3c0129c5b6b1182eecee6ab92a57355b92cd0d58 | Publicada e verificada |
| backup/migration-20261106/history/3cf1c2472179 | 3cf1c2472179bb46033e9a15e33eec3d07e7dad4 | 3cf1c2472179bb46033e9a15e33eec3d07e7dad4 | Publicada e verificada |
| backup/migration-20261106/history/46623ed08dab | 46623ed08dab8a725538b86977c815da31b1af74 | 46623ed08dab8a725538b86977c815da31b1af74 | Publicada e verificada |
| backup/migration-20261106/history/476b32c95a1c | 476b32c95a1c7dbbdcf5e9228cf31a89b90a699d | 476b32c95a1c7dbbdcf5e9228cf31a89b90a699d | Publicada e verificada |
| backup/migration-20261106/history/5a1d0f3280c7 | 5a1d0f3280c7b38aca649f48c3b27ee5816ecb05 | 5a1d0f3280c7b38aca649f48c3b27ee5816ecb05 | Publicada e verificada |
| backup/migration-20261106/history/5accfea7e802 | 5accfea7e8024c709d0f154bf1a1da0557eadfc1 | 5accfea7e8024c709d0f154bf1a1da0557eadfc1 | Publicada e verificada |
| backup/migration-20261106/history/5bc0302cf0a7 | 5bc0302cf0a70d7d844f1a4f68fd625dc082edc1 | 5bc0302cf0a70d7d844f1a4f68fd625dc082edc1 | Publicada e verificada |
| backup/migration-20261106/history/5d5c1298b91f | 5d5c1298b91fec2fdc429a279eee575553fbaba4 | 5d5c1298b91fec2fdc429a279eee575553fbaba4 | Publicada e verificada |
| backup/migration-20261106/history/61d61c6e1191 | 61d61c6e1191d066b69c767822dc620d3f84a10f | 61d61c6e1191d066b69c767822dc620d3f84a10f | Publicada e verificada |
| backup/migration-20261106/history/6528b94ff0a5 | 6528b94ff0a5f0cba22d57838a282e59b907c29b | 6528b94ff0a5f0cba22d57838a282e59b907c29b | Publicada e verificada |
| backup/migration-20261106/history/66994e8afc4b | 66994e8afc4bdbceae6db6a02147a65987a61116 | 66994e8afc4bdbceae6db6a02147a65987a61116 | Publicada e verificada |
| backup/migration-20261106/history/71ed7c0e27f3 | 71ed7c0e27f343d3084e81884679cea15e76d879 | 71ed7c0e27f343d3084e81884679cea15e76d879 | Publicada e verificada |
| backup/migration-20261106/history/74927bec8277 | 74927bec8277b0630c752214e82fa2981eb22c95 | 74927bec8277b0630c752214e82fa2981eb22c95 | Publicada e verificada |
| backup/migration-20261106/history/7b63cc0724f1 | 7b63cc0724f17656d62839d4a119afc8ba3bf15a | 7b63cc0724f17656d62839d4a119afc8ba3bf15a | Publicada e verificada |
| backup/migration-20261106/history/85ed6c16f6d8 | 85ed6c16f6d8f5f7d06181310f48ff72ef7cd68e | 85ed6c16f6d8f5f7d06181310f48ff72ef7cd68e | Publicada e verificada |
| backup/migration-20261106/history/9375139e64c5 | 9375139e64c5b8d0862b842b35de618f394b172a | 9375139e64c5b8d0862b842b35de618f394b172a | Publicada e verificada |
| backup/migration-20261106/history/9614754a6028 | 9614754a60283a9c2fe879a9bb6fce3dcceaa8fd | 9614754a60283a9c2fe879a9bb6fce3dcceaa8fd | Publicada e verificada |
| backup/migration-20261106/history/979990b388e1 | 979990b388e15541d59af60135c65c3dc3d4ffdb | 979990b388e15541d59af60135c65c3dc3d4ffdb | Publicada e verificada |
| backup/migration-20261106/history/98a2f94437cc | 98a2f94437cc054fc700d94ed5d539116004e935 | 98a2f94437cc054fc700d94ed5d539116004e935 | Publicada e verificada |
| backup/migration-20261106/history/9ab112cf260b | 9ab112cf260b2b2a66a742ae58de626a564fe61a | 9ab112cf260b2b2a66a742ae58de626a564fe61a | Publicada e verificada |
| backup/migration-20261106/history/9ac92f1c9da6 | 9ac92f1c9da64c83e0d2eaec5de112fe3d997a30 | 9ac92f1c9da64c83e0d2eaec5de112fe3d997a30 | Publicada e verificada |
| backup/migration-20261106/history/a2420f1eb69a | a2420f1eb69a0f8aead4f286d4659fb2fe4f3544 | a2420f1eb69a0f8aead4f286d4659fb2fe4f3544 | Publicada e verificada |
| backup/migration-20261106/history/a3986002e9f9 | a3986002e9f9810d9acdd90dbca86efb2745a340 | a3986002e9f9810d9acdd90dbca86efb2745a340 | Publicada e verificada |
| backup/migration-20261106/history/a465c79f08c0 | a465c79f08c0d5d14481034166997a25d3c06e69 | a465c79f08c0d5d14481034166997a25d3c06e69 | Publicada e verificada |
| backup/migration-20261106/history/a87d115d5090 | a87d115d50904756251e99bf02adccb33d612250 | a87d115d50904756251e99bf02adccb33d612250 | Publicada e verificada |
| backup/migration-20261106/history/ab14993a1b10 | ab14993a1b10e4dc81a1e55733a52999578fe4c4 | ab14993a1b10e4dc81a1e55733a52999578fe4c4 | Publicada e verificada |
| backup/migration-20261106/history/af2a81d3d38b | af2a81d3d38b7f8e622320c28a7ade40c2f62357 | af2a81d3d38b7f8e622320c28a7ade40c2f62357 | Publicada e verificada |
| backup/migration-20261106/history/b2612c1635ee | b2612c1635eefb8ac72cb7ef1a73e0a3bacb8af5 | b2612c1635eefb8ac72cb7ef1a73e0a3bacb8af5 | Publicada e verificada |
| backup/migration-20261106/history/b265d2fba755 | b265d2fba7559f0ea9b1cebd0897b3724a955886 | b265d2fba7559f0ea9b1cebd0897b3724a955886 | Publicada e verificada |
| backup/migration-20261106/history/b2e76dfbbb16 | b2e76dfbbb1601f8d25c8380fa16ddec54d1ca67 | b2e76dfbbb1601f8d25c8380fa16ddec54d1ca67 | Publicada e verificada |
| backup/migration-20261106/history/b43ce81bfd23 | b43ce81bfd23f70bcfad883f0dc8aaeabdb162c7 | b43ce81bfd23f70bcfad883f0dc8aaeabdb162c7 | Publicada e verificada |
| backup/migration-20261106/history/b44c5676a4e9 | b44c5676a4e9c7f19fd933de3b3e73b3736b29ce | b44c5676a4e9c7f19fd933de3b3e73b3736b29ce | Publicada e verificada |
| backup/migration-20261106/history/b80ee6507cde | b80ee6507cde6a59140cbb98ce1430b8c9fd749e | b80ee6507cde6a59140cbb98ce1430b8c9fd749e | Publicada e verificada |
| backup/migration-20261106/history/b82059fc1d3e | b82059fc1d3e5f522f027c356fe2b47b4586bae8 | b82059fc1d3e5f522f027c356fe2b47b4586bae8 | Publicada e verificada |
| backup/migration-20261106/history/bd2c6b199f70 | bd2c6b199f7020679d9bba5c450646236cf1e76a | bd2c6b199f7020679d9bba5c450646236cf1e76a | Publicada e verificada |
| backup/migration-20261106/history/c015403148e8 | c015403148e8fa6f51a4c5800d0f6da2a1f85ae8 | c015403148e8fa6f51a4c5800d0f6da2a1f85ae8 | Publicada e verificada |
| backup/migration-20261106/history/c6c37ea2c51f | c6c37ea2c51f41e70e6709a027c12148bc66a38f | c6c37ea2c51f41e70e6709a027c12148bc66a38f | Publicada e verificada |
| backup/migration-20261106/history/c72d39da08b8 | c72d39da08b803abedab50595e6cb51c59f2856f | c72d39da08b803abedab50595e6cb51c59f2856f | Publicada e verificada |
| backup/migration-20261106/history/c9407db9b676 | c9407db9b6766a4f3be3e24fc792ace4687d9be3 | c9407db9b6766a4f3be3e24fc792ace4687d9be3 | Publicada e verificada |
| backup/migration-20261106/history/cdd5005a0ca6 | cdd5005a0ca6443f28acdb66d094390c61183141 | cdd5005a0ca6443f28acdb66d094390c61183141 | Publicada e verificada |
| backup/migration-20261106/history/cf1bd080dde9 | cf1bd080dde995a74717f9d8f291d3998ae6487f | cf1bd080dde995a74717f9d8f291d3998ae6487f | Publicada e verificada |
| backup/migration-20261106/history/d637082f6967 | d637082f696786f13e7b3073d0bb8fc5b10c1b5c | d637082f696786f13e7b3073d0bb8fc5b10c1b5c | Publicada e verificada |
| backup/migration-20261106/history/d8c7917f8b85 | d8c7917f8b853cce93c81705e98d65039f8453ed | d8c7917f8b853cce93c81705e98d65039f8453ed | Publicada e verificada |
| backup/migration-20261106/history/d902fe31ee72 | d902fe31ee72662e662f177db5ab86f9446741c1 | d902fe31ee72662e662f177db5ab86f9446741c1 | Publicada e verificada |
| backup/migration-20261106/history/dacc1f7b4cb7 | dacc1f7b4cb7e1be6738abde49dd932d16f9a455 | dacc1f7b4cb7e1be6738abde49dd932d16f9a455 | Publicada e verificada |
| backup/migration-20261106/history/e495bcd50784 | e495bcd507843654716a2a8b4c91888c20cf3faf | e495bcd507843654716a2a8b4c91888c20cf3faf | Publicada e verificada |
| backup/migration-20261106/history/e5900f67f07d | e5900f67f07d6d82fa9a356005450a9c6a7e7100 | e5900f67f07d6d82fa9a356005450a9c6a7e7100 | Publicada e verificada |
| backup/migration-20261106/history/e7abac73ae5e | e7abac73ae5e5dd2577639a25b165630e078bdf0 | e7abac73ae5e5dd2577639a25b165630e078bdf0 | Publicada e verificada |
| backup/migration-20261106/history/e8cf98019dce | e8cf98019dcef5d926fccdf89004360054823a24 | e8cf98019dcef5d926fccdf89004360054823a24 | Publicada e verificada |
| backup/migration-20261106/history/f24a9f6ceadf | f24a9f6ceadf801f15d976bec542ad835c5fb511 | f24a9f6ceadf801f15d976bec542ad835c5fb511 | Publicada e verificada |
| backup/migration-20261106/history/f593994a5137 | f593994a5137a32018042c6e0db8f66fafa3e0ea | f593994a5137a32018042c6e0db8f66fafa3e0ea | Publicada e verificada |
| backup/migration-20261106/history/fd78f4d263cf | fd78f4d263cf265fcccc4865b067cde1b7305255 | fd78f4d263cf265fcccc4865b067cde1b7305255 | Publicada e verificada |
| backup/migration-20261106/history/fd7a4aa92725 | fd7a4aa9272598190a53a6c5bde6364b60920198 | fd7a4aa9272598190a53a6c5bde6364b60920198 | Publicada e verificada |
| backup/migration-20261106/local-main | e8e5e0f0045a23a9d8e4e5bb108e634171999ae3 | e8e5e0f0045a23a9d8e4e5bb108e634171999ae3 | Publicada e verificada |
| chore/d4-03-release-readiness | fd97fd39b58656b45bf5b65c3a8c46353b2f24dc | fd97fd39b58656b45bf5b65c3a8c46353b2f24dc | Publicada e verificada |
| chore/d4-05-dependency-security | 780d92b8a0dbf2143e1784ef4395fbea9c2d8d90 | 780d92b8a0dbf2143e1784ef4395fbea9c2d8d90 | Publicada e verificada |
| codex/d4-01-review-1148 | 47c3ff998e5d92cbc624662478247a4c09e0eb34 | 47c3ff998e5d92cbc624662478247a4c09e0eb34 | Publicada e verificada |
| codex/d4-02-review-1148 | b81b4a0652445ac8ea35ca9a9a429b1fc40b615d | b81b4a0652445ac8ea35ca9a9a429b1fc40b615d | Publicada e verificada |
| codex/d4-04-review-1148 | 33d17d71742bcc5ab2b03682303b91f047afff6c | 33d17d71742bcc5ab2b03682303b91f047afff6c | Publicada e verificada |
| codex/d4-09-concurrency-investigation | d37071743e45b9bf5a341a2bd2119f1c43af03fc | d37071743e45b9bf5a341a2bd2119f1c43af03fc | Publicada e verificada |
| codex/d4-09-stage3-review | 5a568d6052924a387ce6f5bfba763106f9c3ae24 | 5a568d6052924a387ce6f5bfba763106f9c3ae24 | Publicada e verificada |
| codex/d4-09-validated-snapshot | 7961bc647936089a1a29a0e1e4326160aa9a23cb | 7961bc647936089a1a29a0e1e4326160aa9a23cb | Publicada e verificada |
| codex/dev4-stage3-integration | cf9b09cefb0f9cf5d120012dd7a7f330c99569c8 | cf9b09cefb0f9cf5d120012dd7a7f330c99569c8 | Publicada e verificada |
| codex/fix-pr47 | 98339f9f0147b97df5ed1aa77ec97dc7152f45ac | 98339f9f0147b97df5ed1aa77ec97dc7152f45ac | Publicada e verificada |
| codex/fix-pr49 | 9421d74caeb349600439a19455e75c51290a6cec | 9421d74caeb349600439a19455e75c51290a6cec | Publicada e verificada |
| codex/fix-pr50 | e40f151bbff9d6318f936547e61b7d84a4f557c1 | e40f151bbff9d6318f936547e61b7d84a4f557c1 | Publicada e verificada |
| codex/pr23-upload-coverage | 3de6f46f1dd9f76042a844880315e0da7a2d5899 | 3de6f46f1dd9f76042a844880315e0da7a2d5899 | Publicada e verificada |
| codex/pr24-privacy-fixes | 6a952beb91d5b566040ffba63e5fb0c9263cf32e | 6a952beb91d5b566040ffba63e5fb0c9263cf32e | Publicada e verificada |
| codex/pr25-admin-access-tests | 098fdfee8ca55b4c17e479066300f215b8d6dd32 | 098fdfee8ca55b4c17e479066300f215b8d6dd32 | Publicada e verificada |
| codex/pr27-benchmark-evidence | b4b6cdfabde2de9fc1830bbaa91efa5dc711088c | b4b6cdfabde2de9fc1830bbaa91efa5dc711088c | Publicada e verificada |
| codex/reconcile-pr38 | 2d5c56d58ee20d782f7ac1656cf78006c5604450 | 2d5c56d58ee20d782f7ac1656cf78006c5604450 | Publicada e verificada |
| codex/review-drafts | e25783ff8d0c9af6bb945b1a154d17abf5aded45 | e25783ff8d0c9af6bb945b1a154d17abf5aded45 | Publicada e verificada |
| codex/review-pr42 | a6d70067f7401f2b066eed9d87e7571c65cbd3c8 | a6d70067f7401f2b066eed9d87e7571c65cbd3c8 | Publicada e verificada |
| codex/review-pr44 | e55ad03ab70a795428d8a0a23298a42189406e1b | e55ad03ab70a795428d8a0a23298a42189406e1b | Publicada e verificada |
| codex/review-pr45 | 60a05a999bd41bf3ab32395334ae1a088b6b0efa | 60a05a999bd41bf3ab32395334ae1a088b6b0efa | Publicada e verificada |
| codex/review-pr46 | 2f0b8c0f7c28134a4ac2eb77eeaf77047691f0d0 | 2f0b8c0f7c28134a4ac2eb77eeaf77047691f0d0 | Publicada e verificada |
| codex/review-pr47 | a1f6109c0c14574091186a9c2f23e34705224818 | a1f6109c0c14574091186a9c2f23e34705224818 | Publicada e verificada |
| codex/review-pr49 | f085df4aedeecc17f6b6b55cb651204dc4693ccd | f085df4aedeecc17f6b6b55cb651204dc4693ccd | Publicada e verificada |
| codex/review-pr50 | 92837f76ebeffa1496d009d6fcbd6dc80aecde0f | 92837f76ebeffa1496d009d6fcbd6dc80aecde0f | Publicada e verificada |
| feat/d4-06-private-pilot | 7ee31394234924175e8a058d7b0fee199462f4d1 | 7ee31394234924175e8a058d7b0fee199462f4d1 | Publicada e verificada |
| feat/d4-07-observability | 04eef5f98cc5f61a653469d83d4e57dcc46b47df | 04eef5f98cc5f61a653469d83d4e57dcc46b47df | Publicada e verificada |
| feat/d4-08-backup-recovery | 90852d3bdbe7304f05b9dd5d5aa6669b612b3ffd | 90852d3bdbe7304f05b9dd5d5aa6669b612b3ffd | Publicada e verificada |
| feat/d4-10-distributed-processing | 2f3d282525c7721eaa1d9b7a2755b4283d5669dc | 2f3d282525c7721eaa1d9b7a2755b4283d5669dc | Publicada e verificada |
| fix/auditoria-integracao-geral | d49662c6a7a2dc2c74d78cb85431b35b95cd9632 | d49662c6a7a2dc2c74d78cb85431b35b95cd9632 | Já sincronizada |
| fix/d4-04-local-runtime | 345ff4733fb2e6ccf830666a2bf271d82c9888b7 | 345ff4733fb2e6ccf830666a2bf271d82c9888b7 | Publicada e verificada |
| test/d4-01-pr22-integration | d55689baa98c2276750df04f53ade7ea0ba757ff | d55689baa98c2276750df04f53ade7ea0ba757ff | Publicada e verificada |
| test/d4-02-demo-isolation | 6a6ce6cd0c66015719e17654b7c7e6f0428c487e | 6a6ce6cd0c66015719e17654b7c7e6f0428c487e | Publicada e verificada |
| test/d4-09-adversarial-scenarios | 168d3ea2ba7966c7ddecdad6c9997bf39f84b421 | 168d3ea2ba7966c7ddecdad6c9997bf39f84b421 | Publicada e verificada |
| backup/migration-20261106/dev4-evidence | 93cf0391102d007089337cd0704ecac3c0ee9020 | 93cf0391102d007089337cd0704ecac3c0ee9020 | Publicada e verificada |
| backup/migration-20261106/worktree-DocRisk-dev4-race-baseline | b271b5725e838acd64723edcb5d45cde3e3b5999 | b271b5725e838acd64723edcb5d45cde3e3b5999 | Publicada e verificada |
| backup/migration-20261106/worktree-DocRisk-review42 | 90f6ee1c4668442706744913772f5d1e905d4e97 | 90f6ee1c4668442706744913772f5d1e905d4e97 | Publicada e verificada |
| backup/migration-20261106/worktree-DocRisk-review44 | 2f67e40e8074e170badc978ead01fc99be566f01 | 2f67e40e8074e170badc978ead01fc99be566f01 | Publicada e verificada |
| backup/migration-20261106/worktree-DocRisk-review45 | 3bfdd38df2be6ee2e123c6d9e06aa07eb9b347a8 | 3bfdd38df2be6ee2e123c6d9e06aa07eb9b347a8 | Publicada e verificada |
| backup/migration-20261106/review49-evidence | 8280616c4b583156a0020dbdbcb3d0e85a71c5c2 | 8280616c4b583156a0020dbdbcb3d0e85a71c5c2 | Publicada e verificada |
| backup/migration-20261106/dev4-raw-logs | 43d307da972c249193133397b9ca86f75cc1cecc | 43d307da972c249193133397b9ca86f75cc1cecc | Publicada e verificada |


Principais referências: d370717 original, 5a568d6 revisão D4-09 e cf9b09c integração combinada estão acessíveis. As versões históricas D4-01 47c3ff9, D4-02 b81b4a0 e D4-04 33d17d7 também. A integração não foi substituída por outra branch. Branches de revisão já incorporadas à main também tiveram nomes preservados.

## C. Arquivos e evidências

Foram preservados 319 arquivos exatos, com SHA-256 e origem em evidence-file-manifest.json. Incluem os três relatórios de etapas, nota Dev1/Dev2, quatro textos de PR, manifesto JSON e commits efetivamente aplicados, testes concorrentes, relatórios de runtime/isolation, saídas com falhas e logs brutos de ensaios sintéticos. INDEX_EVIDENCIAS.md fornece links imutáveis. Foram preservadas também três imagens e um PDF de prévia do parecer, visualmente verificados como inteiramente fictícios, em branch própria de evidência Dev3.

Os 319 arquivos incluem 124 logs de ensaios locais e 21 evidências antes guardadas em .git/dev4-audit. Arquivos repetidos em diretórios diferentes foram mantidos para conservar a proveniência. Os dois testes D4-09 que falham mantêm suas funções e asserts originais, sem skip/xfail e sem correção. Foram verificados no conteúdo baixado do GitHub, não apenas no objeto local.

Não publicados: api/.env, bancos SQLite/WAL e diretórios de uploads/páginas, estados temporários de testes, node_modules, ambientes virtuais, builds/caches. Três arquivos pip-show de metadados reproduzíveis (d4-05-packages.txt, main-pillow.txt, security-pillow.txt) ficaram locais por conterem contatos de autores upstream, sem relevância para código; as versões estão nos snapshots JSON públicos. Esses arquivos não foram apagados. Arquivos de dados reais ou de proveniência não autorizada não foram enviados.

## D. Operações realizadas

- Fetch e inventário em todos os worktrees encontrados, incluindo stashes e objetos não alcançáveis.
- Inspeção de conteúdo de 97 blobs inéditos de histórico; nove alertas revisados eram leituras de os.getenv, campos vazios de exemplos e credenciais fictícias num teste de rejeição de URL. Nenhuma chave real encontrada nesses objetos.
- Inspeção dos arquivos novos e dos logs, preservação binária exata, teste de estrutura do PDF e revisão visual das três páginas sintéticas. Nenhum .env privado ou banco foi adicionado.
- Criadas 71 referências de preservação histórica (67 commits órfãos, 3 HEADs destacados e 1 main local), preservando as refs originais.
- Oito pushes atômicos de referências explícitas, sem main/force, conferidos por ls-remote. Nenhuma divergência exigiu sobrescrita.
- Criadas sete branches de evidências, com 18 commits de preservação separados por frente/tarefa. Detalhes de cada commit e arquivos em preservation-commits.json. Foram usados objetos/árvores Git novos, sem checkout nem alteração do índice ou dos arquivos das branches em uso. Uma checagem automática de texto PDF interrompeu somente a prévia; após revisão visual, ela foi preservada separadamente. Nenhum trabalho foi descartado.
- Push atômico das sete branches e verificação de 122 refs/319 arquivos num repositório vazio, sem alternates locais. Hashes de cada arquivo conferidos. A branch de guia/relatório adiciona somente documentação/inventário/snapshots de ambiente depois desta verificação.

Os comandos exatos de push e seus resultados estão nos registros locais push-results.json e push-evidence.txt. O relatório não inventa execução nova de testes: trata-se de preservação dos resultados já existentes, inclusive as duas falhas combinadas (485 aprovações, 2 falhas, 1 ignorado).

## E. Pendências e material somente local

TRANSFERÊNCIA PRIVADA PENDENTE: .env e os diretórios de dados listados no guia, incluindo api/data da raiz e seis diretórios de ensaio/revisão. Podem conter tokens e uploads; permanecem nesta máquina e NÃO estão protegidos pelo clone do GitHub. Usar canal/mídia criptografada; assegurar backup SQLite consistente e caminhos remapeados antes de usar no notebook. Não consideramos a migração desses dados concluída.

257 diretórios Temp/docrisk-* foram encontrados. Os logs relevantes dos ensaios/runtime foram enviados; os estados de dados e os diretórios pytest não foram publicados e normalmente são recriáveis. Ambientes/dependências e caches também são recriáveis. Objetos Git soltos sem commit, índices/reflogs e configuração de credenciais permanecem locais; commits relevantes, inclusive os antes sem referência, foram preservados em refs remotas.

A pasta desta operação C:/Users/Pichau/Documents/DocRisk-migration-backup-20261106-074405 contém inventários privados, verificações e scripts operacionais. Relatórios úteis e manifestos são publicados na branch do guia; arquivos de controle local, erros de descoberta e o repositório de verificação não precisam ser enviados. Nenhum segredo foi copiado para relatórios públicos.

## F. Recuperação no notebook

Ver RECUPERAR_NO_NOTEBOOK.md para clone, fetch, worktrees, branches, dependências, configuração privada, hashes e retomada dos dois testes vermelhos. Recomenda-se continuar em nova branch local derivada de origin/codex/d4-09-stage3-review. Recuperar cf9b09c separadamente para a combinação, mantendo d370717 independente.

## G. Segurança e estado técnico

Não foram enviados segredos reais, .env privado, bancos ou arquivos de dados não autorizados. Valores fictícios de testes e modelos vazios de configuração já existentes no código foram preservados, sem editar testes. A checagem combina leitura/inspeção, padrões de segredos, revisão visual dos artefatos e exclusão explícita de dados privados; não é alegação de prova matemática contra qualquer segredo concebível.

Código e evidências revisadas estão preservados no GitHub. Ainda há transferência privada necessária para configuração e dados. Revisões D4-01/02/04, bloqueios AEJ/falha tardia da D4-09, revisão Dev1/Dev2, CI remoto e decisão sobre release continuam pendentes. Nenhum PR foi aberto/integrado. Não há release candidate congelada nem vídeo concluído. D4-10 não foi implementada. Backup não equivale a aprovação de integração.
