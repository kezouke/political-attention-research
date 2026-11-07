"""Validate and report the release comparison from public aggregate outputs."""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data/processed/three_explanations/manifesto_refresh"


def main():
    replay = json.loads((P / "version_replay_checks.json").read_text())
    assert replay["numerical_version_comparison_completed"]
    assert replay["original_outputs_unchanged"]
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == value
               for name, value in replay["original_outputs_sha256"].items())
    inputs = [P / "programme_decomposition_2026a.csv", P / "programme_coverage_2026a.csv",
              P / "coverage_version_comparison.csv", P / "estimate_version_comparison.csv",
              P / "primary_version_summary.csv", P / "version_replay_checks.json"]
    new = pd.read_csv(inputs[0])
    assert np.allclose(new.change_pp, new.within_pp + new.reweight_pp + new.roster_pp, atol=1e-8)
    assert np.allclose(new.raw_change_pp, new.raw_within_pp + new.raw_reweight_pp + new.raw_roster_pp, atol=1e-8)
    coverage = pd.read_csv(inputs[2])
    compared = pd.read_csv(inputs[3])
    common = compared[compared["_merge"].eq("both")]
    for c in ["change_pp", "within_pp", "reweight_pp", "roster_pp"]:
        assert np.allclose(common[c + "_difference"], common[c + "_2026a"] - common[c + "_2023a"], atol=1e-8)
    bank = common[common["sample"].eq("main") & common.topic.eq("economy") & common.kind_2023a.eq("banking")]
    calm = common[common["sample"].eq("main") & common.topic.eq("economy") & common.kind_2023a.eq("comparison")]
    changed = coverage[coverage["sample"].eq("main") & coverage.status_2023a.ne(coverage.status_2026a)].copy()
    summary = pd.read_csv(inputs[4])
    matched_rows = []
    for kind, q in [("banking", bank), ("comparison", calm)]:
        for version in ["2023a", "2026a"]:
            matched_rows.append({"kind": kind, "version": version, "n": len(q),
                "increase": int(q[f"change_pp_{version}"].gt(0).sum()),
                "decrease": int(q[f"change_pp_{version}"].lt(0).sum()),
                "within_largest": int(q[f"within_pp_{version}"].abs().gt(q[[f"reweight_pp_{version}", f"roster_pp_{version}"]].abs().max(axis=1)).sum()),
                "mean_change_pp": q[f"change_pp_{version}"].mean(),
                "median_change_pp": q[f"change_pp_{version}"].median()})
    matched = pd.DataFrame(matched_rows)
    matched.to_csv(P / "matched_version_summary.csv", index=False, float_format="%.12g")
    bank_max = float(bank.change_pp_difference.abs().max())
    checks = {
        "candidate_rows": replay["candidate_rows"],
        "candidate_estimate_rows": len(new),
        "decomposition_identities_pass": True,
        "comparison_deltas_pass": True,
        "original_outputs_unchanged": True,
        "banking_common_pairs": len(bank),
        "banking_sign_changes": int(bank.change_sign_differs.sum()),
        "banking_max_absolute_revision_pp": bank_max,
        "calm_common_pairs": len(calm),
        "calm_common_sign_changes": int(calm.change_sign_differs.sum()),
        "main_coverage_status_changes": len(changed),
        "raw_data_read_by_this_report": False,
        "report_driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
    }
    (P / "release_comparison_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n")
    assert len(bank) == 16 and not bank.change_sign_differs.any()
    assert len(calm) == 73 and len(changed) == 4
    rows = []
    for q in summary[summary.scope.eq("all_eligible_pairs")].itertuples():
        rows.append(f"| {q.version} | {'Кризисные' if q.kind == 'banking' else 'Спокойные'} | {q.n} | {q.increase} | {q.decrease} | {q.within_largest} |")
    matched_table = []
    for q in matched[matched.kind.eq("comparison")].itertuples():
        matched_table.append(f"| {q.version} | {q.n} | {q.increase} | {q.decrease} | {q.within_largest} |")
    coverage_table = []
    for q in changed.itertuples():
        coverage_table.append(f"| {q.pair_id} | {q.pre_coverage_2023a:.2f} / {q.post_coverage_2023a:.2f} | {q.pre_coverage_2026a:.2f} / {q.post_coverage_2026a:.2f} | {q.status_2023a} → {q.status_2026a} |")
    bank_table = []
    for q in bank.sort_values("pair_id").itertuples():
        bank_table.append(f"| {q.pair_id} | {q.change_pp_2023a:+.4f} | {q.change_pp_2026a:+.4f} | {q.change_pp_difference:+.6f} |")
    text = f"""# Проверка Manifesto Project 2026a

Обновление данных сохраняет основной вывод о программах: в тех же 16
кризисных эпизодах доля экономических тем выросла в восьми и снизилась
в восьми. Компонент изменения текстов продолжающих участвовать партий
остаётся крупнейшим по модулю в 10 эпизодах. Наибольшее изменение оценки
общего сдвига между выпусками составляет {bank_max:.6f} процентного пункта.

Это проверка чувствительности к версии источника, а не независимая
репликация или оценка причинного влияния кризиса. Правила были закреплены
в [спецификации](planning/manifesto-refresh-specification.md) до получения
числового файла 2026a. Основная статья и её график сохраняют явно названный
выпуск 2023a; новый выпуск представлен отдельной проверкой.

## Источники и точность пересчёта

После завершения регистрации скачан официальный
[Manifesto Project 2026a](https://doi.org/10.25522/manifesto.mpds.2026a):
5 330 строк и 175 столбцов. SHA-256 файла:
`{replay['candidate_sha256']}`.
Его ключи совпадают с официальным каталогом документов. Источник:
Lehmann, Pola; Franzmann, Simon; Al-Gaddooa, Denise; Ivanusch, Christoph;
Riethmüller, Felicia; Samstag, Svenja; Volkens, Andrea; Weßels, Bernhard;
Zehnter, Lisa (2026). *The Manifesto Data Collection. Manifesto Project
(MRG/CMP/MARPOR). Version 2026a*. WZB / IfDem.

Скрипт 88 сначала воспроизводит 2023a. Все 1 722 строки покрытия,
8 130 строк оценок и 350 сводных строк совпали с сохранёнными CSV в пределах
их восьми значащих цифр. Исходные результаты не перезаписаны. Затем те же
календарные пары, десять определений тем и семь вариантов отбора применены
к 2026a. Проверены тождества разложения во всех {len(new):,} новых строках
оценок. В этих подсчётах одна и та же пара повторяется для разных тем и
вариантов отбора; строки не являются независимыми кризисами.

## Основной набор в каждом выпуске

| Выпуск | Интервалы | Число | Рост экономической доли | Снижение | Изменение текстов крупнейшее |
|---|---|---:|---:|---:|---:|
{chr(10).join(rows)}

В обоих выпусках 75 спокойных интервалов, но это не полностью одинаковые
наборы. Два интервала добавились, два выбыли. Поэтому разницу между 51 и
52 нельзя целиком приписать исправлениям значений на прежней выборке.

На 73 спокойных интервалах, присутствующих в обоих выпусках:

| Выпуск | Общие интервалы | Рост | Снижение | Изменение текстов крупнейшее |
|---|---:|---:|---:|---:|
{chr(10).join(matched_table)}

Один знак общего экономического сдвига меняется: Боливия 2009–2014,
с +0,071 до −2,032 п. п. В целом вывод сохраняется: преобладание компонента
переписывания программ встречается и в спокойные периоды, поэтому само
по себе не является особым признаком кризиса. Результаты не доказывают
равенство распределений в кризисные и спокойные периоды.

## Почему изменился контрольный набор

Таблица показывает долю голосов, покрытую подходящими документами до и
после интервала. Прежний порог 75% на каждом конце не менялся.

| Интервал | Покрытие 2023a, % | Покрытие 2026a, % | Решение |
|---|---:|---:|---|
{chr(10).join(coverage_table)}

В обновлении появились недостающие программы Канады 2019 года и Валлонии
2019 года. Для Польши 2015 года исправлены типы программ: один документ
переведён из типа 1 в 6, другой из 8 в 4. Прежнее правило включает типы
1, 2 и 8; новое описание документов поэтому снижает подходящее покрытие
этого конца сравнения. Изменения документированы авторами в
[release notes](https://manifestoproject.wzb.eu/down/data/2026a/codebooks/release_notes_MPDS2026a.pdf).
Исключённые интервалы не удалены из исходной версии 2023a.

## Изменения по всем 16 кризисным эпизодам

Общий сдвиг экономической доли, процентные пункты:

| Эпизод | 2023a | 2026a | Разница выпусков |
|---|---:|---:|---:|
{chr(10).join(bank_table)}

## Воспроизведение и ограничения

После самостоятельного получения лицензированных исходных файлов:

```sh
python analysis/88_manifesto_version_replay.py --candidate data/raw/manifesto_refresh_20261107/manifesto_2026a.csv
python analysis/89_manifesto_refresh_report.py
```

Вторая команда использует только публичные агрегаты. Полные таблицы по всем
темам и вариантам отбора находятся в
[manifesto_refresh](data/processed/three_explanations/manifesto_refresh/).
`matched_version_summary.csv` отделяет сравнение общих интервалов от изменения
набора; `coverage_version_comparison.csv` сохраняет все решения об отборе.
Исходные программные строки не распространяются.

Новый выпуск не устраняет ограничения тематики: она не измеряет внимание
граждан, конкретное обещание помощи или причинный механизм. Пересчёт здесь
касается программного разложения. Отрицательный прогноз на 89 парах выборов
остаётся результатом исходного эксперимента 2023a; его качество на 2026a
этой проверкой не оценивалось.
"""
    (ROOT / "MANIFESTO_REFRESH.md").write_text(text)
    print(json.dumps({k: v for k, v in checks.items() if k != "sha256"}, indent=2))


if __name__ == "__main__":
    main()
