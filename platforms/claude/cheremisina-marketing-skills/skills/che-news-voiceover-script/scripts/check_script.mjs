#!/usr/bin/env node

import fs from "node:fs";

const filePath = process.argv[2];
if (!filePath) {
  console.error("Usage: node scripts/check_script.mjs <file> [--wpm 135] [--target-seconds 120] [--pause-seconds 3] [--greeting single|omit]");
  process.exit(2);
}

const options = { wpm: 135, "target-seconds": 120, "pause-seconds": 3, greeting: "omit", "greeting-text": "", "author-gender": "unspecified" };
for (let i = 3; i < process.argv.length; i += 2) {
  const flag = process.argv[i];
  const key = flag.startsWith("--") ? flag.slice(2) : "";
  const raw = process.argv[i + 1];
  if (!Object.hasOwn(options, key) || raw === undefined) {
    console.error(`Unknown option or missing value: ${flag}`);
    process.exit(2);
  }
  options[key] = ["greeting", "greeting-text", "author-gender"].includes(key) ? raw : Number(raw);
}
if (![options.wpm, options["target-seconds"], options["pause-seconds"]].every(Number.isFinite)
    || options.wpm <= 0 || options["target-seconds"] <= 0 || options["pause-seconds"] < 0
    || options["pause-seconds"] >= options["target-seconds"]
    || !["single", "omit"].includes(options.greeting)
    || !["unspecified", "female", "male", "neutral"].includes(options["author-gender"])) {
  console.error("Invalid timing or greeting options");
  process.exit(2);
}

let source;
try {
  source = fs.readFileSync(filePath, "utf8");
} catch {
  console.error("Cannot read input script; provide an existing readable UTF-8 file.");
  process.exit(2);
}

function section(name, nextNames) {
  const heading = new RegExp(`^#{1,6}\\s+${name}\\s*$`, "imu");
  const match = heading.exec(source);
  if (!match) return null;
  const start = match.index + match[0].length;
  const rest = source.slice(start);
  const nextHeading = new RegExp(
    `^#{1,6}\\s+(?:${nextNames.join("|")})\\s*$`,
    "imu",
  ).exec(rest);
  return (nextHeading ? rest.slice(0, nextHeading.index) : rest).trim();
}

function wordList(value) {
  return value.match(/[\p{L}\p{N}]+(?:[-‑][\p{L}\p{N}]+)*/gu) ?? [];
}

function sentenceWordCounts(value) {
  return value
    .split(/(?<=[.!?])\s+(?=[А-ЯA-ZЁ«])/u)
    .map((sentence) => ({ sentence: sentence.trim(), words: wordList(sentence).length }))
    .filter((item) => item.sentence);
}

const speech =
  section("Текст для озвучки", ["Дисклеймер", "Контроль", "Факт-чек"]) ?? source.trim();
const disclosure = section("Дисклеймер", ["Контроль", "Факт-чек"]) ?? "";
const greetingText = options["greeting-text"];
const greetingMatches = greetingText ? speech.split(greetingText).slice(1) : [];
const hasOpeningGreeting = Boolean(greetingText) && speech.startsWith(greetingText);
const greetingWords = hasOpeningGreeting ? wordList(greetingText).length : 0;
const core = hasOpeningGreeting ? speech.slice(greetingText.length).trim() : speech;
const wordCount = wordList(core).length;
const disclosurePending = !disclosure || /Нужна утверждённая редакция дисклеймера/iu.test(disclosure);
const disclosureWords = disclosurePending ? 0 : wordList(disclosure).length;
const questionCount = (core.match(/\?/g) ?? []).length;
const enumeratorCount = (
  core.match(/(?:во-первых|во-вторых|в-третьих|наконец|итак)/giu) ?? []
).length;
const masculineAuthor =
  core.match(/(?<!\p{L})(?:я уверен|я советовал|я бы рекомендовал|я сам)(?!\p{L})/giu) ?? [];
const staleDisclosure = `${speech}\n${disclosure}`.match(/нейроведущ/giu) ?? [];
const intensifiers = core.match(
  /(?<!\p{L})(?:абсолютно|идеальн\p{L}*|нулев\p{L}*|мгновенн\p{L}*|точно|всегда|никогда|доказал\p{L}*|единственн\p{L}*)(?!\p{L})/giu,
) ?? [];
const digitTokens = core.match(/\b\d+(?:[.,]\d+)?%?\b/g) ?? [];
const longSentences = sentenceWordCounts(core).filter((item) => item.words > 28);
const markdownArtifacts = core.match(/(?:https?:\/\/|^\s*[-*]\s+|^\s*\|.+\|\s*$)/gmu) ?? [];

const failures = [];
const warnings = [];

if (options.greeting === "single" && (!hasOpeningGreeting || greetingMatches.length !== 1)) {
  failures.push("Нужно одно заданное приветствие в начале (--greeting-text)");
}
if (options.greeting === "omit" && greetingMatches.length) {
  failures.push("В продолжении подборки или при отменённом приветствии представление нужно убрать");
}
if (hasOpeningGreeting && !speech.slice(greetingText.length).startsWith("\n\n")) {
  warnings.push("Отделите приветствие от новости пустой строкой для смысловой паузы");
}
if (options["author-gender"] === "female" && masculineAuthor.length) failures.push(`Мужская форма авторского голоса: ${masculineAuthor.join(", ")}`);
if (staleDisclosure.length) failures.push("Устаревшее упоминание нейроведущих в дисклеймере");
if (!wordCount) failures.push("Основной текст пуст");
if (disclosurePending) warnings.push("Дисклеймер отсутствует или не утверждён: полная длительность неизвестна");
if (questionCount > 3) warnings.push(`Более трёх риторических вопросов: ${questionCount}`);
if (enumeratorCount < 2 || enumeratorCount > 4) {
  warnings.push(`Нет ясной триады или слишком много нумерующих переходов: ${enumeratorCount}`);
}
if (intensifiers.length) {
  warnings.push(`Проверить усилители по статье: ${[...new Set(intensifiers)].join(", ")}`);
}
if (digitTokens.length) {
  warnings.push(`Проверить произношение и смысл чисел: ${[...new Set(digitTokens)].join(", ")}`);
}
if (longSentences.length) {
  warnings.push(`Предложения длиннее 28 слов: ${longSentences.length}`);
}
if (markdownArtifacts.length) warnings.push("В речи найдены URL, список или таблица");

const spokenWords = greetingWords + wordCount + disclosureWords;
const estimatedSeconds = Math.round((spokenWords / options.wpm) * 60 + options["pause-seconds"]);
const budget = Math.floor((options["target-seconds"] - options["pause-seconds"]) * options.wpm / 60)
  - (options.greeting === "single" ? wordList(greetingText).length : 0) - disclosureWords;
if (!disclosurePending && budget < 1) failures.push("Приветствие и дисклеймер не оставляют времени для новости");
if (!disclosurePending && Math.abs(estimatedSeconds - options["target-seconds"]) > 10) {
  warnings.push(`Расчётная длительность отличается от цели более чем на 10 секунд: ${estimatedSeconds} с; бюджет основного текста ${budget} слов`);
}
const result = {
  status: failures.length ? "fail" : warnings.length ? "warn" : "pass",
  scope: "mechanical_checks_only",
  editorial_review_required: true,
  readiness: "not_established_by_this_checker",
  metrics: {
    greeting_words: greetingWords,
    core_words: wordCount,
    disclosure_words: disclosureWords,
    spoken_words: spokenWords,
    wpm: options.wpm,
    additional_pause_seconds: options["pause-seconds"],
    target_seconds: options["target-seconds"],
    estimated_seconds: disclosurePending ? null : estimatedSeconds,
    known_text_estimated_seconds: estimatedSeconds,
    target_core_words: disclosurePending ? null : budget,
    paragraph_words: core.split(/\n\s*\n/u).map(p => wordList(p).length),
    rhetorical_questions: questionCount,
    enumerating_transitions: enumeratorCount,
    long_sentences_over_28_words: longSentences.length,
  },
  failures,
  warnings,
};

console.log(JSON.stringify(result, null, 2));
process.exit(failures.length ? 1 : 0);
