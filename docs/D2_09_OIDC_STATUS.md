# D2-09 — Contrato de autenticação OIDC

O módulo `docrisk_core.oidc_sessions` define um fluxo independente de provedor para Authorization Code + PKCE S256, estado de uso único, nonce, sessão opaca, expiração, revogação local e verificação CSRF.

As implementações de `OIDCProvider` precisam validar assinatura e algoritmo do ID token, issuer, audience, expiração, nonce e a política de MFA antes de devolver `OIDCIdentity`. O `SessionStore` precisa guardar o hash do token opaco e remover sessões expiradas ou revogadas. Os stores usados nos testes são apenas adaptadores em memória.

O login operacional continua bloqueado até a equipe definir o provedor, configuração de ambiente, URLs de callback e logout, política de MFA e armazenamento persistente de tentativas/sessões. A autenticação por token da demo só funciona com `DOCRISK_DEMO_MODE=1`; tokens existentes na tabela `users` ou `platform_accounts` não autenticam fora desse modo.

Este contrato não adiciona rotas de login, não substitui o token da demo por OIDC e não configura um provedor. A integração depende da decisão de infraestrutura e do modelo de memberships de D2-10/D4-06.
