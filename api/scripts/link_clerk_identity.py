"""Bootstrap explícito: vincular subject Clerk a conta interna; não envia convites."""
import argparse
import secrets
from datetime import datetime, timezone

from docrisk_core import config, db


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--subject', required=True)
    parser.add_argument('--account-id', required=True)
    parser.add_argument('--platform', action='store_true')
    parser.add_argument('--name', help='Nome institucional para criar o primeiro Admin Geral')
    args = parser.parse_args()
    if config.AUTH_MODE != 'clerk' or not config.CLERK_ISSUER or not args.subject.startswith('user_'):
        parser.error('Configure DOCRISK_AUTH_MODE=clerk, CLERK_ISSUER e informe um subject user_ válido.')
    db.init_db(seed=False)
    with db.tx() as conn:
        existing = conn.execute('SELECT * FROM identity_links WHERE issuer=? AND subject=?', (config.CLERK_ISSUER,args.subject)).fetchall()
        if any(bool(row['platform_account_id']) != args.platform for row in existing):
            parser.error('A identidade institucional não pode ser combinada com contas operacionais.')
        table = 'platform_accounts' if args.platform else 'users'
        if conn.execute(f'SELECT 1 FROM {table} WHERE id=? AND ativo=1', (args.account_id,)).fetchone() is None:
            if args.platform and args.name and args.name.strip():
                conn.execute('INSERT INTO platform_accounts (id,nome,token) VALUES (?,?,?)', (args.account_id,args.name.strip(),secrets.token_urlsafe(48)))
            else:
                parser.error('Conta interna ativa não encontrada.')
        column = 'platform_account_id' if args.platform else 'user_id'
        if conn.execute(f'SELECT 1 FROM identity_links WHERE {column}=?', (args.account_id,)).fetchone():
            parser.error('Esta conta interna já possui identidade vinculada.')
        conn.execute(f'INSERT INTO identity_links (id,issuer,subject,{column},created_at) VALUES (?,?,?,?,?)',
                     (secrets.token_urlsafe(24),config.CLERK_ISSUER,args.subject,args.account_id,datetime.now(timezone.utc).isoformat()))
    print('Vínculo criado. Nenhuma credencial ou convite foi emitido.')


if __name__ == '__main__':
    main()
