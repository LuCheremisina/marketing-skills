"""Explicit delivery of a prepared, validated digest. No subscriber discovery or bot startup."""
import argparse
import hashlib
import json
import os
from pathlib import Path


def recipients(value):
    ids = [int(x.strip()) for x in value.split(',') if x.strip()]
    if not ids or any(x == 0 for x in ids) or len(ids) != len(set(ids)):
        raise argparse.ArgumentTypeError('Нужен непустой список уникальных ненулевых chat_id')
    return ids


def deliver(bundle_path, target_ids, confirmed=False, transport=None, token=None):
    if not confirmed:
        raise ValueError('Отправка требует --confirm-send после разрешения пользователя')
    bundle_path = Path(bundle_path).resolve()
    if bundle_path.is_relative_to(Path(__file__).resolve().parent.parent):
        raise ValueError('Выпуск и журнал доставки должны храниться вне пакета')
    bundle = json.loads(bundle_path.read_text(encoding='utf-8'))
    import collect_and_send as collector
    issues = collector.validate_generated_digest(bundle['digest'], bundle['html'])
    if issues:
        raise ValueError('QA: ' + '; '.join(issues))
    targets = recipients(','.join(str(x) for x in target_ids))
    digest_id = hashlib.sha256(bundle['html'].encode()).hexdigest()
    receipts_path = bundle_path.parent / 'delivery-receipts.json'
    receipts = json.loads(receipts_path.read_text()) if receipts_path.exists() else {}
    done = receipts.setdefault(digest_id, [])
    pending = [x for x in targets if str(x) not in done]
    if not pending:
        return {'status': 'already_sent', 'sent': 0, 'failed': 0}
    token = token or os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError('Среда не предоставила Telegram-доступ')
    if transport is None:
        import requests
        transport = requests.post
    failures = 0
    sent = 0
    for target in pending:
        try:
            response = transport(
                f'https://api.telegram.org/bot{token}/sendDocument',
                data={'chat_id': target},
                files={'document': ('digest.html', bundle['html'].encode(), 'text/html')}, timeout=30)
            response.raise_for_status()
            if not response.json().get('ok'):
                raise RuntimeError('Telegram rejected delivery')
        except Exception as exc:
            # Exception text/URL may contain credentials; report only the class.
            print('[ERROR] Delivery: ' + type(exc).__name__)
            failures += 1
            continue
        sent += 1
        done.append(str(target))
        receipts_path.write_text(json.dumps(receipts), encoding='utf-8')
    if failures == 0:
        history = collector.load_history()
        history.setdefault('sent_hashes', []).extend(
            collector.news_hash(e['title'], e['link']) for e in bundle.get('entries', []))
        history.setdefault('sent_titles', []).extend(collector.normalize_title(t) for t in bundle['titles'])
        history['previous_digest_titles'] = bundle['titles']
        collector.save_history(history)
    return {'status': 'ok' if failures == 0 else 'partial', 'sent': sent, 'failed': failures}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--recipients', type=recipients, required=True)
    parser.add_argument('--confirm-send', action='store_true')
    args = parser.parse_args(argv)
    if not args.confirm_send:
        parser.error('Требуется --confirm-send после проверки разрешения и получателей')
    try:
        result = deliver(args.bundle, args.recipients, confirmed=True)
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result))
    return 0 if result['status'] in {'ok', 'already_sent'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
