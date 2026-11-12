# ESP32 club workshop

Write a little C++, push it, and watch it run on a real ESP32. The boards are plugged into the
instructor's laptop, which builds and flashes every push with GitHub Actions.

## Your first pull request (no wiring needed)
1. Find your board's number (it's on the tape by its USB socket).
2. Make your team's file, `teams/<team-name>.cpp`, from `examples/00_hello.cpp`.
3. Put your board number on the **first line**, and your names in the hello message:
   ```cpp
   // board: 3
   ...
   printf("Hello from Ana and Sam! ...
   ```
4. Open a **pull request**. Its **Checks** tab builds your code, flashes your board, and ends with
   what your board printed. Every later push to the same pull request flashes again.

**In the browser (easiest):** on the repo page open `teams/`, then **Add file → Create new file**,
name it `rockets.cpp`, paste the example, and **Commit changes… → Propose changes → Create pull
request**. GitHub makes your fork for you. To change it later, open the file in *your* fork, edit
it with the pencil icon, and commit to the same branch.

**With git:**
```sh
gh repo fork Yackasone/esp32-workshop --clone    # or Fork on the website, then git clone your fork
cd esp32-workshop
git switch -c rockets
cp examples/00_hello.cpp teams/rockets.cpp       # then edit it
git add teams/rockets.cpp
git commit -m "Say hello"
git push -u origin rockets                       # then open the pull request on GitHub
```
Only `teams/*.cpp` files from a pull request are used. The build runs with this repo's tooling
in a sandbox, and the code can only include `workshop.h` and standard C headers.

## Exercises
`examples/01_blink` … `07_launch`, from one LED to a launch countdown with abort. Each one opens
with its wiring in a comment and ends with a **Try:** challenge. Copy the next one into your team
file (keep the `// board:` line), push, and watch. Pin names (`RED`, `BUTTON`, `BUZZER`…) work on
every chip:

| Name | ESP32-D | ESP32-S3 | ESP32-C6 |
|---|---|---|---|
| RED / YELLOW / GREEN | 25 / 26 / 27 | 7 / 15 / 16 | 21 / 22 / 23 |
| BUTTON / BUZZER | 33 / 32 | 6 / 5 | 2 / 1 |

API: `pinMode`, `digitalWrite`, `digitalRead`, `analogWrite` (0-255), `analogRead` (0-4095),
`tone`, `noTone`, `delay`, `millis`, `randomBetween`, `printf`. See `main/workshop.h`.

## Instructor: the lab laptop
Needs Nix (`nix develop` gives ESP-IDF 5.5) and the boards on a hub (S3/C6: use the UART port).
```sh
./ws doctor && ./ws flash-all 00_hello && ./ws boards   # label each socket with its number
```
Runner, for the session only (runs as you, so stop it afterwards):
```sh
mkdir -p ~/esp32-lab-runner && cd ~/esp32-lab-runner
export RUNNER_ROOT=$PWD
nix shell nixpkgs#github-runner -c config.sh --url https://github.com/<org>/<repo> \
    --token <registration token> --labels esp32-lab --name lab-laptop --unattended --ephemeral=false
nix shell nixpkgs#github-runner -c run.sh
```
Then Actions → "Flash my board" → Run workflow → sketch `prewarm`, so class-time builds take seconds.
The repo is public: pull requests run main's workflow (`pull_request_target`) and compile only
their `teams/*.cpp` inside bubblewrap, so a stranger's PR can flash a board but can't reach the
laptop. Keep it that way: never add a `pull_request` trigger.
Afterwards: Ctrl+C the runner and remove it in Settings → Actions → Runners.

Local commands still work (`./ws run 07_launch 3`, `./ws capture 3`); the shared lock makes them
wait their turn with the runner.
