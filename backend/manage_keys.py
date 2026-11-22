"""5-bosqich: Terminaldan foydalanuvchilar (Access Key) boshqaruv skripti."""
import argparse
from datetime import datetime, timedelta, timezone
import secrets

from database import (
    create_user_record,
    delete_user_record,
    init_db,
    list_all_users,
    update_user_record,
)


def main() -> None:
    init_db()
    parser = argparse.ArgumentParser(description="YouTube UZ Tarjimon — Parollar boshqaruvi")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="Barcha foydalanuvchilarni ko'rish")

    p_add = sub.add_parser("add", help="Yangi foydalanuvchi qo'shish")
    p_add.add_argument("name", help="Foydalanuvchi ismi")
    p_add.add_argument("--key", default="", help="Maxsus parol (bo'sh qolsa avtomatik)")
    p_add.add_argument("--days", type=int, default=30, help="Muddat (kunlarda, 0 = cheksiz)")
    p_add.add_argument("--vip", action="store_true", help="ElevenLabs VIP ovozga ruxsat")
    p_add.add_argument("--vip-limit", type=int, default=20, help="Kunlik VIP limit")

    p_block = sub.add_parser("block", help="Foydalanuvchini bloklash")
    p_block.add_argument("key", help="Access Key")

    p_unblock = sub.add_parser("unblock", help="Foydalanuvchini faollashtirish")
    p_unblock.add_argument("key", help="Access Key")

    p_del = sub.add_parser("delete", help="Foydalanuvchini o'chirish")
    p_del.add_argument("key", help="Access Key")

    args = parser.parse_args()

    if args.cmd == "list":
        for u in list_all_users():
            status = "FAOL" if u["is_active"] else "BLOK"
            vip = f"VIP({u['vip_used_today']}/{u['vip_daily_limit']})" if u["allow_vip"] else "-"
            exp = (u["expires_at"] or "Cheksiz")[:10]
            print(f"{u['access_key']:16} | {u['name']:16} | {status:4} | {exp:10} | {vip}")
    elif args.cmd == "add":
        key = args.key.strip().upper() or f"UZ-{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"
        exp = (datetime.now(timezone.utc) + timedelta(days=args.days)).isoformat() if args.days > 0 else None
        user = create_user_record(key, args.name.strip(), exp, args.vip, args.vip_limit)
        print(f"Qo'shildi: {user['name']} -> Parol: {user['access_key']}")
    elif args.cmd == "block":
        print("Bloklandi" if update_user_record(args.key, is_active=False) else "Topilmadi")
    elif args.cmd == "unblock":
        print("Faollashtirildi" if update_user_record(args.key, is_active=True) else "Topilmadi")
    elif args.cmd == "delete":
        print("O'chirildi" if delete_user_record(args.key) else "Topilmadi yoki admin")


if __name__ == "__main__":
    main()
