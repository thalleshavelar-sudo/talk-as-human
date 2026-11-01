#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const NAME = "talk-as-human";
const ROOT = path.resolve(__dirname, "..");
const PAYLOAD = ["SKILL.md", "references", "scripts", "LICENSE", "THIRD_PARTY_NOTICES.md"];
const VERSION = require(path.join(ROOT, "package.json")).version;

const HELP = `${NAME} ${VERSION}

Usage:
  npx ${NAME}                     install for every project (~/.claude/skills/${NAME})
  npx ${NAME} --project           install in this project (./.claude/skills/${NAME})
  npx ${NAME} --dir <path>        install into <path>/${NAME} (other agents' skill folders)
  npx ${NAME} uninstall [--project | --dir <path>]
  npx ${NAME} check <file|-> [--channel chat|work|email|commit|post|review|doc] [--strict] [--min 1|2|3]

Options:
  --force      overwrite an existing install without asking
  -h, --help   show this help
  -v, --version
`;

function parse(argv) {
  const opts = { cmd: "install", project: false, dir: null, force: false, rest: [] };
  const args = argv.slice();
  if (args[0] && !args[0].startsWith("-")) opts.cmd = args.shift();
  if (opts.cmd === "check") { opts.rest = args; return opts; }
  while (args.length) {
    const a = args.shift();
    if (a === "--project" || a === "-p") opts.project = true;
    else if (a === "--dir" || a === "-d") opts.dir = args.shift();
    else if (a === "--force" || a === "-f") opts.force = true;
    else if (a === "-h" || a === "--help") opts.cmd = "help";
    else if (a === "-v" || a === "--version") opts.cmd = "version";
    else fail(`Unknown option: ${a}\n\n${HELP}`);
  }
  return opts;
}

function fail(msg) {
  process.stderr.write(msg.endsWith("\n") ? msg : msg + "\n");
  process.exit(1);
}

function target(opts) {
  if (opts.dir) return path.resolve(opts.dir, NAME);
  if (opts.project) return path.resolve(process.cwd(), ".claude", "skills", NAME);
  return path.join(os.homedir(), ".claude", "skills", NAME);
}

function install(opts) {
  const dest = target(opts);
  if (fs.existsSync(dest)) {
    const marker = path.join(dest, "SKILL.md");
    if (!fs.existsSync(marker) && !opts.force) {
      fail(`${dest} exists and doesn't look like ${NAME}. Use --force to overwrite it.`);
    }
    fs.rmSync(dest, { recursive: true, force: true });
  }
  fs.mkdirSync(dest, { recursive: true });
  for (const item of PAYLOAD) {
    const src = path.join(ROOT, item);
    if (fs.existsSync(src)) fs.cpSync(src, path.join(dest, item), { recursive: true });
  }
  try { fs.chmodSync(path.join(dest, "scripts", "check_ai_tells.py"), 0o755); } catch (_) {}
  console.log(`Installed ${NAME} ${VERSION} to ${dest}`);
  console.log(`In Claude Code, run /${NAME} or just ask it to make a text sound natural.`);
}

function uninstall(opts) {
  const dest = target(opts);
  if (!fs.existsSync(path.join(dest, "SKILL.md"))) fail(`Nothing to remove at ${dest}`);
  fs.rmSync(dest, { recursive: true, force: true });
  console.log(`Removed ${dest}`);
}

function check(rest) {
  if (!rest.length) fail(`Pass a file, or - to read stdin.\n\n${HELP}`);
  const script = path.join(ROOT, "scripts", "check_ai_tells.py");
  for (const py of ["python3", "python"]) {
    const r = spawnSync(py, [script, ...rest], { stdio: "inherit" });
    if (r.error && r.error.code === "ENOENT") continue;
    process.exit(r.status === null ? 1 : r.status);
  }
  fail("The checker needs Python 3 (python3 or python on your PATH).");
}

const opts = parse(process.argv.slice(2));
switch (opts.cmd) {
  case "install": install(opts); break;
  case "uninstall": case "remove": uninstall(opts); break;
  case "check": check(opts.rest); break;
  case "help": process.stdout.write(HELP); break;
  case "version": console.log(VERSION); break;
  default: fail(`Unknown command: ${opts.cmd}\n\n${HELP}`);
}
