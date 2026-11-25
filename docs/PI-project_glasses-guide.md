# PI-project_glasses: complete project guide

Prepared 15 September 2026. Raspberry Pi camera glasses, phone interface, local hand and object detection, and experimental PC chess analysis.

This guide explains the commands and architecture used throughout the project. It separates the working implementation from experiments and proposed upgrades. It is a reference, not a script to paste from beginning to end. Running every historical installation or overwrite command would replace working files with older versions. No API key or password is included.

The PC chess source code inspected for this edition is included in the appendix. The Pi descriptions come from your pasted scripts and terminal output; the Pi filesystem was not independently audited for this edition. Your inline chess photo is visible in the conversation, but its original JPG/PNG was not available as a local file for model inference. Actual piece recognition on your set remains unverified.

# 1. What runs where

The Pi Zero 2 W runs Raspberry Pi OS/Raspbian 13 (trixie), a 32-bit armv7l system with Python 3.13.5. Your camera identifies itself as imx708_wide_noir: Camera Module 3 Wide NoIR. Its maximum sensor image is 4608 by 2592 pixels. The memory output you shared reported 424 MiB total RAM; that was a historical reading, not a current measurement.

For the original glasses application, the Pi captures images and serves a web page. Your phone opens that page over Wi-Fi. Preview and capture do not require your PC. On confirmation, the Pi sends the selected JPEG to Gemini and returns the answer to the phone. That last operation needs Internet access and valid API credentials.

Hand tracking and generic object detection run in the browser on whichever device opens the page. On your phone, your phone performs that inference; on your PC, the PC browser performs it. The input is still the Pi camera image, not the phone camera. Downloading the model initially may require Internet access even though subsequent inference happens locally.

Chess mode is a separate PC application. The Pi supplies JPEG frames over your home network, the PC tracks the board and keeps chess state, and Stockfish calculates a move on the PC CPU. Your RTX 4060 is available hardware, but this version does not use CUDA or the GPU. For chess mode the PC must remain on; this is the exception you explicitly allowed.

The current chess application does not classify individual chess pieces from pixels. It starts from a known standard position, compares square appearance after movement, proposes legal moves, and waits for your confirmation. A correct green board outline does not prove that the pieces have been recognized.

## Addresses and ports

http://192.168.0.164:8000 is the Pi camera application using the IPv4 address shown in your terminal. Your router may assign a different address later. Port 8000 identifies the camera web service.

http://localhost:8001 is the PC chess page when opened on that same PC. On a phone, localhost means the phone itself. To open PC chess from the phone, use http://PC-LAN-IP:8001, replacing PC-LAN-IP with the PC's Wi-Fi/LAN IPv4 address. The devices must be able to reach each other on the same network. Keep these services on your trusted local network; they do not implement user login.

# 2. Understanding the terminal commands

Commands labelled Pi/Bash belong in the SSH terminal connected to the Pi. Commands labelled PC/PowerShell belong in the Windows project terminal. Markdown fences such as ```bash are formatting, not part of the commands. Do not paste backslashes introduced by chat formatting before underscores or the tilde.

On the Pi, ~ means your home directory, normally /home/hadi. A relative filename depends on the current directory. An absolute filename begins with /. On Windows the repository is C:\Users\hdacc\OneDrive\Desktop\ray-ponder.

A command's first word is its program. Remaining words are arguments. Options commonly begin with - or --. Quotes preserve spaces and stop special interpretation. sudo runs an individual command with elevated Linux privileges; systemctl --user manages your own user service and normally needs no sudo.

## Writing a file with a heredoc

The following is a syntax example only; the placeholder is not a working server.

```bash
cat > ~/example.txt <<'END'
Text to put in the file.
END
```

cat reads the text between the opening and closing markers. The > operator creates or replaces the destination file. Quoting 'END' prevents Bash from expanding variables or command substitutions inside the text. The closing END must be on its own line. The >> operator would append instead of replacing. A shell waiting for the closing marker is not necessarily frozen.

Python patch commands of the form python3 - <<'PY' use the same mechanism: the - tells Python to read the program from standard input. pathlib.Path selects a file, read_text reads it, replace changes matching text, and write_text writes the result. Such patches depend on the original text matching exactly. They should not be replayed on an unrelated version of server.py.

Ctrl+C interrupts a foreground program. If that program is a log viewer, the service keeps running. If it is the actual manually launched server, the server stops. Closing SSH does not stop a properly configured lingering systemd service.

# 3. Pi inventory and camera checks

Pi/Bash: these commands report information without modifying your project.

```bash
cat /etc/os-release
uname -m
python3 --version
free -h
hostname -I
rpicam-hello --list-cameras
```

cat prints the operating-system identification file. uname -m reports CPU userspace architecture; armv7l explains why an ordinary 64-bit Python wheel cannot simply be installed here. python3 --version reports the Python interpreter version. free -h prints memory and swap in readable units. Available memory is more useful than the free column alone because Linux uses spare memory for caches.

hostname -I prints network addresses. Use the Pi's reachable LAN IPv4 address in your phone URL. rpicam-hello --list-cameras asks the camera stack to enumerate sensors and supported modes. The initially empty list was explained by the disconnected camera; after connection, imx708_wide_noir appeared.

For physical camera work, shut down the Pi and disconnect power before changing the ribbon. Camera recognition is a separate step from starting Flask or hand tracking.

## Packages and a single test image

Pi/Bash: these installation commands are for the Pi, not Windows.

```bash
sudo apt update
sudo apt install -y --no-install-recommends python3-picamera2 python3-flask python3-waitress
rpicam-still --nopreview --timeout 3000 --output ~/camera-test.jpg
ls -lh ~/camera-test.jpg
```

apt update refreshes package indexes; it does not by itself upgrade every installed package. apt install installs the named packages and required dependencies. -y accepts the normal package confirmation. --no-install-recommends omits optional recommended packages. Picamera2 connects Python to the Raspberry Pi camera stack. Flask defines web routes. Waitress serves HTTP requests with worker threads.

rpicam-still takes one image. --nopreview avoids a display window, useful over SSH. --timeout 3000 allows three seconds before capture. --output selects the JPEG path. ls -lh checks that the file exists and shows its size. A successful capture proves the camera works independently of your web code. Stop your camera service before a standalone test if it already owns the camera.

# 4. Camera server and live preview

Your application directory is normally ~/lens-camera and its entry point is server.py. Creating a directory with mkdir -p is repeatable: -p creates missing parent directories and does not fail merely because the directory already exists.

```bash
mkdir -p ~/lens-camera
python3 ~/lens-camera/server.py
```

The second command runs the server in the foreground for diagnosis. Do not run it while the service owns the same camera. It also does not automatically inherit the EnvironmentFile settings used by systemd, so an API-key error in this manual context may differ from the service's environment.

## How an image reaches the phone

Picamera2 configures and opens the sensor. Frames pass through the Pi camera pipeline. In your later script the main stream is YUV420 at 1920 by 1080, a requested 20 frames per second, four buffers, and continuous autofocus. Requested frame rate is a target; exposure, processing load and transport can reduce the observed rate.

MJPEGEncoder produces JPEG frames for an MJPEG stream. The code uses a 16,000,000-bit/s encoder setting. That number is not a guaranteed network rate or a guarantee of visual quality. The camera output class stores the most recent complete JPEG, increments a sequence number, and signals a threading.Condition. Waiting clients wake when a new frame arrives.

The /frame route returns one current JPEG. The /stream route returns a multipart response containing successive JPEGs. The browser can display /stream as an image element. Each part has a boundary, content type and image bytes. This is MJPEG, not H.264 or WebRTC.

The original polling preview requested a JPEG every 400 milliseconds. Even without other overhead that only allows 2.5 updates per second. Reducing the wait to 100 milliseconds raises the theoretical limit to 10 requests per second. MJPEG avoids that repeated request cycle, but Wi-Fi, browser decoding and simultaneous inference still matter.

Keeping only the latest frame helps prevent an ever-growing queue of old images. Waitress threads allow several requests to progress concurrently; a long-lived stream occupies a thread. Eight worker threads and a smaller output high-water mark were used in the later Pi server. These settings do not make every slow client fast.

## Resolution, latency and heat

A 1920 by 1080 preview has 2,073,600 pixels. A 1280 by 720 preview has 921,600 pixels. The larger image contains 2.25 times as many pixels to encode, transfer and decode. Maximum resolution and minimum delay are competing goals on a Pi Zero 2 W. Raising JPEG quality also increases data volume.

The 4608 by 2592 sensor maximum is not the configured live-preview size. A proposed full-resolution still capture was a separate idea; do not assume it exists in the latest pasted streaming script. In that script, snapping freezes the chosen JPEG from the stream.

Continuous autofocus can adjust as you move your head. Low light can require longer exposure, increasing blur and reducing useful tracking detail. The NoIR camera also admits infrared light; its colours may differ from an ordinary camera. Increasing resolution cannot reconstruct a hidden piece or undo motion blur.

# 5. Snap, confirm and Gemini

The phone captures a JPEG from the Pi feed and holds it for review. A Save link lets you keep that selected image. Confirmation sends that same chosen image for analysis, so the answer should correspond to the preview you approved rather than a later camera frame.

The Pi converts the image bytes to base64 for the JSON API request. Base64 adds roughly one third to the byte count. The generateContent request contains a text prompt and inline image data with a JPEG MIME type. The x-goog-api-key header carries the credential. The model returns structured JSON whose text parts become the displayed answer.

The application needs a finite upstream timeout and must restore the button state when a request fails. A page left at 'Analyzing photo' can mean an unfinished request, a server exception, or frontend error handling that never clears the busy state. Camera startup logs alone do not reveal the Gemini error; inspect logs while reproducing one analysis request.

## Where the key belongs

The PC's .env.local does not automatically configure the Pi. The Pi user service reads ~/.config/lens-camera/environment. Keep the key on the Pi server side rather than putting it into browser JavaScript. The custom X-Lens-Request header used by the app is not user authentication.

Pi/Bash: run the read command separately, paste the key at its hidden prompt, and press Enter. The terminal deliberately does not echo the key.

```bash
mkdir -p ~/.config/lens-camera
chmod 700 ~/.config/lens-camera
read -r -s -p "Paste your Gemini API key, then press Enter: " LENS_KEY
```

-r reads backslashes literally. -s disables echo. -p supplies the prompt text. LENS_KEY is a temporary shell variable name; you do not replace that word with the secret in the command itself.

After the hidden prompt has finished, the following writes the service configuration. This replaces the existing environment file. The model name shown records the project configuration discussed in this session; model availability and account access can change.

```bash
echo
(umask 077; printf 'GEMINI_API_KEY=%s\nGEMINI_MODEL=gemini-3.5-flash\n' "$LENS_KEY" > ~/.config/lens-camera/environment)
unset LENS_KEY
chmod 600 ~/.config/lens-camera/environment
```

echo moves to a fresh terminal line. The parentheses limit umask to a subshell. umask 077 prevents group/other permissions on newly created files. printf substitutes the key at %s and writes real newline characters at \n. chmod 600 also restricts an already-existing file; umask alone would not change its old permissions. unset removes the temporary shell variable. Never paste the environment file into a support message.

HTTP 401 means the API rejected authentication. In your session replacing the invalid credential resolved it. A quota error, model-not-found error and timeout are different problems and should not all be described as a broken camera. Gemini is an external service with its own terms and quotas; local hand tracking and Stockfish do not make Gemini unlimited or permanently free.

# 6. Automatic startup with systemd

A service lets Linux start your server after boot and supervise it independently of the SSH session. The user service file belongs at ~/.config/systemd/user/lens-camera.service. The following is the unit used for the project; creating it replaces a unit with the same name.

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/lens-camera.service <<'SERVICE'
[Unit]
Description=Lens camera and Gemini app

[Service]
Type=simple
WorkingDirectory=%h/lens-camera
EnvironmentFile=%h/.config/lens-camera/environment
ExecStart=/usr/bin/python3 %h/lens-camera/server.py
Restart=on-failure
RestartSec=5
UMask=0077

[Install]
WantedBy=default.target
SERVICE
```

Description is a human-readable label. Type=simple tells systemd to supervise the launched process directly. WorkingDirectory determines where relative filenames resolve. %h is systemd's home-directory expansion, not Bash syntax. EnvironmentFile loads the key and model settings. ExecStart names the exact interpreter and script, avoiding dependence on an interactive shell's PATH.

Restart=on-failure retries if the process exits abnormally. RestartSec=5 waits five seconds between retries. It does not solve a persistent bug; repeated restarts require reading the error. UMask=0077 restricts permissions on files the process creates. WantedBy=default.target declares the user-session target under which enable installs the startup link.

```bash
sudo loginctl enable-linger "$(whoami)"
systemctl --user daemon-reload
systemctl --user enable --now lens-camera.service
systemctl --user status lens-camera.service --no-pager
```

whoami returns the current username and $(...) substitutes it. enable-linger keeps that user's service manager available without an active login, including boot startup. daemon-reload rereads edited unit files. enable installs the startup relationship; --now also starts the service immediately. status shows the latest state. --no-pager prints normally instead of opening an interactive pager.

An 'active (running)' status milliseconds after startup only proves the process existed then. Your screenshot later showed status=1/FAILURE and auto-restart, so the application was crashing after launch. Recheck after it has had time to initialize.

## Routine service control

```bash
systemctl --user restart lens-camera.service
systemctl --user stop lens-camera.service
systemctl --user start lens-camera.service
systemctl --user is-enabled lens-camera.service
```

These are alternatives for different situations, not a sequence to run every time. restart loads changes to server.py or the service environment by launching a new process. stop releases the camera if shutdown is clean. start launches a stopped service. is-enabled checks whether boot startup is configured. Editing the unit itself also requires daemon-reload; editing only Python code does not.

Do not start a second server.py while this service is running. The sensor pipeline is an exclusive resource. Your 'Failed to acquire camera: Device or resource busy' traceback means another process already owns it. Stop the known camera program before testing, rather than indiscriminately killing every Python process.

# 7. Logs, connectivity, shutdown and temperature

Pi/Bash: choose the relevant diagnostic.

```bash
journalctl --user -u lens-camera.service -n 40 --no-pager
sudo journalctl _SYSTEMD_USER_UNIT=lens-camera.service -n 40 --no-pager
sudo journalctl _SYSTEMD_USER_UNIT=lens-camera.service -f -n 10
```

journalctl reads the system journal. -u filters by unit in the first command; --user selects the user journal. If that says 'No journal files were found', the second command queries the system journal with the user-unit metadata filter. -n limits output to the latest lines. -f follows new messages as they arrive. Trigger the failing action on your phone while following logs, then Ctrl+C exits the viewer.

```bash
curl -I --max-time 10 http://127.0.0.1:8000
curl -I --max-time 10 http://127.0.0.1:8000/static/mediapipe/vision_bundle.js
hostname -I
```

127.0.0.1 is loopback on the machine running curl. -I requests response headers with HEAD. --max-time 10 prevents an indefinite wait. 'Could not connect to server' means no reachable listener accepted that connection; inspect the service before changing browser code. HTTP 200 for the bundle means that route served a file, not that model inference succeeded. Content-Type: text/javascript is appropriate for the script response you showed.

If Pi-local HTTP works but Safari cannot open the page, use the Pi LAN address with http:// and port 8000, and verify Wi-Fi connectivity. Do not use the PC or phone's localhost for the Pi. A guest network may prevent devices communicating. Do not expose the service through router port forwarding to solve a local connectivity problem.

## Shutdown and startup

```bash
sudo poweroff
```

This tells Linux to stop services and flush filesystem writes before powering down. Wait for shutdown to finish before disconnecting the supply. The Pi normally starts again when power is restored. With the enabled lingering service, you then open its camera URL from the phone. Your PC is unnecessary for the original camera/Gemini mode.

```bash
sudo reboot
```

reboot performs an orderly shutdown and restarts. It disconnects SSH temporarily. Neither command relocates your project files. Avoid removing power while the SD card is being written.

## Check heat instead of guessing

```bash
vcgencmd measure_temp
vcgencmd get_throttled
```

measure_temp reports the current SoC temperature. get_throttled returns a bitmask that can include current and past undervoltage or throttling conditions; a nonzero value needs decoding, not a blanket conclusion that the Pi is overheating now. No current temperature was successfully read remotely for this guide. The attempted passwordless SSH connection was rejected, so the earlier warmth report remains unmeasured.

For glasses, leave ventilation around the board and avoid pressing hot electronics against skin. Lowering resolution or processing frequency can reduce load; do not overclock as a response to a lagging browser. A temperature reading and a check for throttling distinguish thermal limits from Wi-Fi or frontend bottlenecks.

# 8. Saving PI-project_glasses on the Pi

A named folder is a backup, not a different program by itself. The active service still points at ~/lens-camera/server.py until its unit is deliberately changed. Copying only Python also misses locally hosted JavaScript and model assets.

Pi/Bash: this repeatable command creates a timestamped backup directory beneath ~/PI-project_glasses, preserving the app directory including static assets and separately copying service configuration. It includes the private API environment file, so keep the backup private.

```bash
backup_dir="$HOME/PI-project_glasses/backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup_dir"
chmod 700 "$HOME/PI-project_glasses" "$backup_dir"
cp -a "$HOME/lens-camera" "$backup_dir/"
cp "$HOME/.config/systemd/user/lens-camera.service" "$backup_dir/"
cp "$HOME/.config/lens-camera/environment" "$backup_dir/"
chmod 600 "$backup_dir/environment"
printf 'Backup saved to %s\n' "$backup_dir"
```

The variable backup_dir holds the destination without repurposing HOME. date creates a sortable timestamp. cp -a recursively copies the application and preserves useful metadata. Quoting paths protects spaces. The final printf prints the backup path, not its secret contents.

This is a file backup, not a full SD-card image. It does not reinstall Raspberry Pi OS or apt packages on a replacement card. For restoration you need the camera packages, the app files, the private environment file in its original configuration directory, the unit file, and the enable-linger/service enable steps. Keep another private backup outside the SD card if you need protection against SD failure.

# 9. Hand tracking in the phone or PC browser

The Pi's limited memory and 32-bit Python environment made browser-side inference the practical path. MediaPipe Hand Landmarker reads a reduced camera image and estimates 21 landmarks per hand. These are inferred joint positions, not measurements of finger bones. When fingers are hidden behind a bottle, the model can lose the hand or produce a poor estimate.

The worker-based script requests a frame from /frame, decodes it with createImageBitmap, resizes it using an OffscreenCanvas, and passes it to the model. Landmark coordinates are mapped onto an overlay that covers the displayed feed. The Pi keeps supplying camera frames while the browser performs this work.

In the discussed versions, inference sizes changed from 480 by 270 to 640 by 360, with up to two hands and a short pause between requests. An 80-millisecond pause does not guarantee 12.5 detections per second: inference and fetching add time. Smoothing combined a large share of the new landmark with a smaller share of the previous one, reducing jitter at the cost of some response delay.

## Why the worker errors happened

A JavaScript module worker does not support importScripts. A classic worker does. The initial module/classic mismatch therefore failed before detecting any hand. Changing only the filename does not change the worker type.

The chosen MediaPipe tasks-vision version was 0.10.21. Attempts to fetch vision_bundle.js and then vision_bundle.cjs from the CDN failed. The project then hosted the bundle locally at /static/mediapipe/vision_bundle.js. The filename on your server can end in .js while containing the downloaded compatible bundle; the file content and loading mechanism must agree.

The classic-worker adaptation temporarily provides self.exports, imports the compatible bundle, retrieves its exports, and removes the temporary export object. The task's WASM runtime and trained model are separate assets. Successfully serving the JavaScript bundle does not prove the WASM files or model have loaded.

Your later HTTP 200 response with JavaScript content type confirmed local bundle delivery. Your subsequent report that tracking worked confirmed a browser-level result. The implementation should surface which stage failed rather than reporting every failure as a missing hand.

## Why tracking can slow the view

Decoding JPEGs, copying canvas pixels and neural inference all consume browser resources. Running hand and object workers simultaneously increases demand. A worker keeps synchronous inference away from the page's main JavaScript thread, but it still competes for CPU, memory and graphics resources. Dimming the room can increase motion blur; adding light helps the input but does not repair an incorrect loading path.

Stop or pause inference while reviewing a photo or when the page is hidden. Use one active camera tab. Prefer a fresh frame after inference completes rather than an unbounded queue. Draw overlays independently of inference frequency so the live view can remain responsive.

# 10. Generic object detection and gestures

The free generic detector explored here was TensorFlow.js COCO-SSD with the lite_mobilenet_v2 backbone. It predicts a fixed set of everyday categories, including bottle. It cannot name everything in the scene, identify arbitrary products, or distinguish chess king, queen, rook and knight as twelve side-specific classes.

The discussed browser assets were TensorFlow.js 4.22.0 and COCO-SSD 2.2.3, hosted under static/bottles. Hosting their JavaScript locally does not automatically host their neural weights locally. The object worker processed a reduced frame, used a confidence threshold and returned boxes with labels. The measured time must include inference when judging real responsiveness.

Several gesture interfaces were tried: pinching near an object, one hand touching while the other opens, pointing near a detected object, and finally opening both palms to display all supported objects. These were successive experiments, not four simultaneous requirements to reinstall.

A gesture selects which detections to show; it does not create a detection the model missed. If the raw detector sees a bottle but the live overlay shows nothing, inspect coordinate scaling, gesture conditions and result-age filters. The diagnostic detector page used the same input image to show raw model output and timing, separating model failure from overlay filtering.

Rejecting results older than 2.5 seconds can hide all output on a slow browser. Allowing older results may make boxes appear, but those boxes describe an earlier frame and can drift from moving objects. Increasing the allowed age does not make inference faster. The final both-palms idea needs the same distinction between fresh video and periodic recognition.

For reliable selection when holding objects, do not require every finger to remain visible behind the object. A separate clear gesture can trigger or lock the selected detection. The UI should show whether it is waiting for a gesture, running detection, or unable to find a supported object.

# 11. PC chess environment and installation

The PC chess application lives in chess-mode inside the Windows repository. It is separate from the web project's package.json and frontend routes. Running npm is not how this Python chess server starts.

PC/PowerShell: start from the repository root.

```powershell
Set-Location 'C:\Users\hdacc\OneDrive\Desktop\ray-ponder'
uv python install 3.12
uv venv --python 3.12 chess-mode/.venv
uv --system-certs pip install --python chess-mode/.venv/Scripts/python.exe -r chess-mode/requirements.txt
```

These are setup commands for a new environment; do not recreate a functioning environment unnecessarily. uv must already be installed and reachable. uv python install obtains a compatible Python interpreter. uv venv creates an isolated package environment at the specified path. The installed interpreter for this project was Python 3.12.14, independent of the Pi's Python 3.13.5.

uv pip install installs the requirements into that explicitly named interpreter. --system-certs uses the operating system certificate trust store; it was used to address certificate verification problems without disabling TLS verification. The earlier --native-tls spelling was deprecated. A Python environment created this way need not contain the pip module; uv can still manage its packages.

The requirements provide Flask for routes, Waitress for HTTP serving, OpenCV headless for image processing, NumPy for arrays, and python-chess for rules, notation and engine communication. Headless OpenCV omits desktop display integration; the images appear in your web browser instead. The requirements file uses version ranges, so a future fresh install is not a byte-identical environment lock.

## Inspecting tools and files

```powershell
Get-Location
Get-Content chess-mode/requirements.txt
Get-Content chess-mode/README.md
nvidia-smi
```

Get-Location confirms the working directory. Get-Content prints selected nonsecret files. nvidia-smi reports the NVIDIA GPU and driver state if the NVIDIA tools are installed. Your reported RTX 4060 does not imply that every library automatically uses it. Current optical flow and Stockfish run on CPU.

During development, read-only git status and git diff inspect existing changes, and rg searches source text efficiently. No command needs to print .env.local to explain the app. The repository's AGENTS.md warns that it is connected to Lovable: do not rewrite already-pushed history with force pushes or destructive rebases.

# 12. Installing and understanding Stockfish

Stockfish is a chess engine. It reads a chess position, searches legal continuations and returns a move. It does not read the camera image or identify physical pieces. Sending it an incorrect digital board can produce an excellent move for the wrong position.

The project uses the official generic Windows Stockfish 18 build. Its executable is under chess-mode/engine/stockfish-18/stockfish/stockfish-windows-x86-64.exe. The downloaded archive retains license/source materials. The local engine does not call a paid API.

PC/PowerShell: these show the download and extraction operations used for that version. They are installation steps, not needed each time you play.

```powershell
New-Item -ItemType Directory -Force chess-mode/engine
Invoke-WebRequest -Uri 'https://github.com/official-stockfish/Stockfish/releases/download/sf_18/stockfish-windows-x86-64.zip' -OutFile chess-mode/engine/stockfish-18.zip
Expand-Archive -LiteralPath chess-mode/engine/stockfish-18.zip -DestinationPath chess-mode/engine/stockfish-18
```

New-Item creates the directory. -Force tolerates an existing directory. Invoke-WebRequest downloads the archive to -OutFile. Expand-Archive extracts it. Do not assume an archive can be repeatedly extracted onto modified contents without checking the destination. STOCKFISH_PATH can point the application to another compatible installed executable.

The Python Engine class uses chess.engine.SimpleEngine.popen_uci. UCI is the text protocol between the controller and engine. It configures two CPU search threads and a 64 MiB hash table, then requests about 0.8 seconds of analysis. Process startup and overhead add to that time. This is a short practical search, not proof of the mathematically best move.

A ThreadPoolExecutor with one worker runs engine analysis away from the request's main work. A board copy prevents the engine job from mutating the live game. Results are associated with a FEN string so an old position's result is not presented as a result for a different current FEN. Cancelling a future does not forcibly interrupt an already-running engine calculation.

The displayed evaluation is from White's perspective: positive favours White and negative favours Black. A mate score is different from a centipawn evaluation. The code formats an ordinary score in pawn units by dividing centipawns by 100. Search depth varies with the position and time budget.

# 13. Launching and using the chess application

PC/PowerShell:

```powershell
chess-mode\.venv\Scripts\python.exe -B chess-mode\app.py
```

The explicit path selects the correct virtual environment without needing an activation script. -B avoids writing .pyc bytecode cache files. app.py launches Waitress on 0.0.0.0 port 8001 with four threads. Binding 0.0.0.0 allows LAN access as well as localhost; it is not the address you type into the phone.

Keep this terminal/process running during chess mode. Open http://localhost:8001 on the PC. The Pi camera service must also be running. The default camera base URL is http://192.168.0.164:8000. To override it for a changed Pi address, set the environment variable before launching:

```powershell
$env:PI_CAMERA_URL = 'http://192.168.0.164:8000'
chess-mode\.venv\Scripts\python.exe -B chess-mode\app.py
```

That variable applies to the current PowerShell process and child processes. It is not a permanent router address reservation.

## Current play sequence

1. Arrange the real pieces in the normal starting position. The current Start game function creates chess.Board(), which assumes that setup.

2. Freeze the calibration image and select the four corners of the 8 by 8 playing area clockwise. Select the actual square grid, not the outside decorative frame.

3. Choose your side and the numbered corner beside a8, Black's queenside rook square. This establishes board orientation; a wrongly chosen a8 rotates square assignment.

4. Start the game. Move a physical piece, take your hand away and let the board settle.

5. Confirm only the proposed move that really occurred, or select the actual move from the legal-move list. Record both players' moves. A legal proposal is not necessarily the observed move.

6. Read the Stockfish suggestion on your turn. If the digital board is wrong, correct the recording before trusting the arrow.

7. Use Undo for a recording mistake and restore the physical board to match. Download PGN before stopping the server; the game is stored in memory.

Your shown board had already-moved pieces, so treating that frame as a standard initial setup would immediately create a mismatch. The current version does not infer an arbitrary starting FEN from the photo.

# 14. How the green board outline follows your head

app.py fetches /frame from the Pi with an eight-second network timeout, limits the downloaded image size, decodes the JPEG and resizes it to 960 by 540. The calibration corners and overlay coordinates use this same image coordinate system.

BoardTracker.calibrate validates four finite points, their image bounds, convex clockwise outline and minimum area of 8,000 pixels. It makes a grayscale image and finds image features inside the board polygon. It requires at least twenty usable features before accepting calibration.

On later frames, Lucas-Kanade optical flow tracks these features from the previous image to the new one. A reverse tracking pass returns them toward their old locations. Tracks with inconsistent forward/backward motion are rejected. At least sixteen remaining tracks are needed.

RANSAC estimates a homography: a perspective transform describing how a flat plane moves between views. The implementation requires at least fourteen inliers, at least 65 percent agreement and feature coverage across at least 20 percent of the board area. It also rejects implausible area changes, nonconvex results, points outside the frame and very large jumps.

The four corners are transformed with that homography and drawn on the latest view. They should change pixel coordinates when your head moves while remaining attached to the physical board. Keeping the same screen coordinates would make the outline slide off the board.

Fresh features are selected after accepted updates. This can still drift: the algorithm tracks visual texture, not the meaning of a chessboard. Hands and tall pieces can move differently from the board plane, and an occluded or blurred board can lose tracking. When tracking is lost, the code hides the valid corner state and requests recalibration. It does not implement guaranteed automatic rediscovery.

# 15. How current move proposals are calculated

The board_image function orders the selected corners using a8 and warps the board to a 480 by 480 square. Each chess square is therefore 60 by 60 pixels. The code converts to grayscale, applies a small Gaussian blur and normalizes average brightness and contrast.

square_changes compares an earlier reference image against the latest steady image. It measures the average absolute pixel difference inside the inner 48 by 48 region of each square, avoiding a six-pixel edge border. Lighting changes, shadows and perspective errors can change that measurement even if a piece has not moved.

rank_moves estimates a background floor from the median square difference. A square counts as changed when its value exceeds both a minimum level and an offset above that floor. Fewer than two or more than eight changed squares produce no ranked proposal. The algorithm enumerates legal moves from the recorded digital position and compares each move's expected changed squares with the measured set.

A proposal score combines set overlap and the concentration of visual difference on the expected squares. The code returns at most five candidates. That score is a heuristic match value, not a calibrated probability that a piece was recognized.

move_squares compares the board before and after each candidate. This naturally includes the rook in castling and the captured pawn square in en passant. Different promotions can share the same changed-square pattern; image change alone cannot identify the promoted piece.

Game.observe waits approximately 0.7 seconds after detected motion before using a steady observation. A recent stable image is required for recording. Game.commit checks the game's version and legality of the submitted UCI move, then updates both the chess board and visual reference. These checks prevent stale or illegal submissions; they do not verify the identity of a physical piece.

## Why the wrong piece can appear to move

A homography is correct for the board plane, but a queen's head is above that plane. As your head moves, the queen can project over a neighbouring square. Shadows also move. The comparison can then rank a different legal move whose squares happen to look changed. Raising image quality alone does not fix that geometric problem.

The green outline and legal-move engine are useful components, but the current heuristic should remain a proposal system requiring confirmation. It cannot satisfy 'understand perfectly which piece is which'. The next stage needs actual piece recognition and uncertainty handling.

## Arrows and state

arrow_points converts the source and destination square centres back through the board perspective transform into image coordinates. The arrow is displayed only when tracking is valid, the board is stable, no unrecorded visual change is present and the suggested move is legal on your turn.

The /state response contains an encoded JPEG, corner coordinates, tracking status and game data. POST /calibrate establishes the outline. POST /game/start initializes the game. POST /game/move records a confirmed move. POST /game/undo reverses a recording. GET /game/pgn exports notation. A shared lock protects these operations, so slow frame retrieval can also delay other requests; extra server threads do not remove that lock.

# 16. The Start game freeze and verification

The earlier freeze after Start game was traced to a NumPy boolean reaching Flask's JSON output. JSON serialization expects a normal Python boolean, not every NumPy scalar type. The changed-state assignment was corrected to explicitly convert the comparison result with bool(...).

This was a concrete server error, not evidence that Stockfish required the GPU or that the Pi camera had physically stopped. Repeated failed /state responses can look like a frozen image in the browser.

PC/PowerShell:

```powershell
chess-mode\.venv\Scripts\python.exe -B -m unittest discover -s chess-mode -p test_game.py
```

-m runs Python's unittest module. discover searches for test modules. -s selects chess-mode as the start directory. -p restricts filenames to test_game.py. The recorded run passed eight tests, including regression coverage for the steady-state JSON response. The source is included in the appendix so the actual test coverage is reviewable.

A separate engine smoke check returned a legal starting-position move. Neither the unit tests nor an engine smoke test establishes recognition accuracy on your physical set. This edition does not claim a real piece-model test on your inline image.

# 17. Planned piece recognition: what must be proved

The intended pipeline is: obtain a clear live frame, track the board, detect each visible piece's type and side, estimate the contact point at its base, map that point to a square, combine consistent observations, ask for correction where ambiguous, and only then update chess state and analyze it.

A piece detector needs twelve semantic labels: white and black pawn, knight, bishop, rook, queen and king. Generic COCO-SSD lacks those labels. A candidate found during preparation is rondinellimorais/chess_recognition, an MIT-licensed repository publishing a chess-specific YOLOv4 configuration and linked trained weights. Its labels distinguish twelve piece/side classes. This is a test candidate, not a validated solution for the purple set.

A bounding box's bottom centre is a useful first approximation to the piece base, but not a guarantee. Occlusion, a clipped box or a tilted view can place it incorrectly. A base-point model or segmentation may be needed. Training on conventional black and white pieces may transfer poorly to purple pieces under a NoIR camera.

The original board JPG/PNG must be available to run the proposed exact-image test. It was not found among the local text attachments. The correct evidence will be an annotated output, raw labels and scores, measured inference time, and a manual check against that same input. A screenshot viewed by the assistant is not equivalent to running model inference on its pixels.

An isolated diagnostic is now prepared in chess-mode/probe_pieces.py, with setup instructions in chess-mode/PIECE-MODEL.md. It uses the downloaded YOLOv4 configuration and class list with OpenCV CPU inference. The following PC command requires your original image at board.jpg and a new output directory:

```powershell
chess-mode\.venv\Scripts\python.exe -B chess-mode/probe_pieces.py board.jpg --output chess-mode/piece-test-01
```

The output is annotated.jpg plus detections.json containing labels, scores, boxes, approximate base points and measured inference time. A base point here is explicitly a box-bottom approximation; this diagnostic does not produce FEN, assign squares, or change the live game. Its --threshold option changes which model scores are shown, not the model's actual ability to recognize a hidden piece.

Only after that test should the detector be connected to live game updates. Measure results over several poses, lighting conditions and moved-piece positions. Keep the last confirmed position while hands cover squares. Do not silently fill an unseen square with an invented piece. Stability across frames can reduce flicker, but repeated confident mistakes remain mistakes.

Even perfect visible piece placement does not reveal all chess state. Side to move, castling rights and en-passant availability depend on game history. An arbitrary midgame scan needs those inputs or a known recorded history before Stockfish can analyze the correct complete position.

For responsive live video, recognition should run on selected recent frames in a separate worker/process and publish its latest result with a timestamp. It should not block the camera route while calculating. The RTX 4060 could accelerate a compatible inference runtime later, but installing ordinary OpenCV wheels does not enable that automatically. No trained model can guarantee zero delay or perfect recognition of hidden pieces.

# 18. Troubleshooting by symptom

Safari cannot open the page: first check Pi service status and Pi-local curl. If local HTTP works, verify the LAN address, port and phone network. If it fails locally, read the Python/service error rather than changing Safari.

Device or resource busy: another camera process owns the sensor. Stop the known service before a standalone capture. Restart the intended service after the test. Avoid running two camera servers.

HTTP 401 from Gemini: verify the Pi service credential, then restart the service after changing its environment. Do not paste the key into logs. The PC .env.local is a separate configuration file.

Analyzing photo forever: inspect the request in logs while reproducing it. A timeout and frontend cleanup are needed even when authentication works. Distinguish a camera capture failure from upstream API failure.

Module scripts do not support importScripts: fix the worker type and compatible bundle-loading strategy. Renaming a module file alone is insufficient.

Bundle route returns 200 but tracking fails: check the actual script content, exports, WASM/model fetches and browser console. HTTP success is only one loading stage.

Hand disappears while gripping a bottle: the bottle may occlude the landmarks. Use a separate visible gesture to select an object rather than requiring an unobstructed gripping hand.

Detector finds a bottle in diagnostics but no live box appears: inspect gesture gating, image/overlay coordinates and freshness filtering. Do not assume the neural model is the failing component.

Preview lags when inference is enabled: lower inference frequency or input size, avoid multiple tabs, and keep a single newest pending frame. Higher resolution increases processing and transfer cost.

Green outline drifts: recalibrate with the full playing area visible. Slow head movement and clearer board features help. Optical flow is not semantic board detection.

Digital pieces differ from the real board: stop relying on the engine arrow. Verify initial setup, a8 orientation and every confirmed move. The present implementation does not identify pieces directly.

Start game freezes: check /state errors. The known NumPy boolean serialization issue was fixed and regression-tested, but future errors should be diagnosed from their own traceback.

Stockfish error: check the executable location and STOCKFISH_PATH. A working camera does not prove the engine binary is present. A working engine does not prove the input position is correct.

Pi feels hot: run measure_temp and get_throttled. No temperature can be inferred accurately from a description of touch. Keep the board ventilated and reduce avoidable load.

# 19. Maintaining and rebuilding this guide

The PDF is generated from docs/PI-project_glasses-guide.md plus an appendix of selected local chess source files. The PDF build reads only this explicit source list; it does not read .env.local, the Pi environment file, or private keys. Long code lines are visually wrapped for print, so use the original source files when copying executable code.

PC/PowerShell: documentation dependencies and generation command.

```powershell
uv --system-certs pip install --python chess-mode/.venv/Scripts/python.exe reportlab pypdf pillow
chess-mode\.venv\Scripts\python.exe -B docs\build_guide.py
```

ReportLab lays out the PDF. pypdf is used for document checks, and Pillow supports image handling. These tools are documentation dependencies, not required for the Pi camera service. The build does not deploy to the Pi or restart either server.

This edition includes the actual PC source as a readable appendix because the precise functions and checks matter. It documents the historical Pi commands and evolution without replaying every earlier text-replacement patch. Replacing a working Pi script requires the complete matching source, not fragments assembled from different chapters.

# 20. Primary references

These references explain the upstream tools. Exact project behaviour is established by the local source included after this chapter. Online package versions, model access and hosted download availability may change.

Raspberry Pi camera software and hardware documentation:
https://www.raspberrypi.com/documentation/accessories/camera.html

Picamera2 manual:
https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf

Raspberry Pi operating-system documentation:
https://www.raspberrypi.com/documentation/computers/os.html

Gemini API keys:
https://ai.google.dev/gemini-api/docs/api-key

Gemini generateContent request reference:
https://ai.google.dev/api/generate-content

MediaPipe Hand Landmarker for the web:
https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/web_js

TensorFlow.js COCO-SSD:
https://github.com/tensorflow/tfjs-models/tree/master/coco-ssd

Official Stockfish 18 release:
https://github.com/official-stockfish/Stockfish/releases/tag/sf_18

python-chess engine interface:
https://python-chess.readthedocs.io/en/latest/engine.html

OpenCV perspective transformations and optical flow:
https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html
https://docs.opencv.org/4.x/d4/dee/tutorial_optical_flow.html

Candidate chess detector, configuration and license:
https://github.com/rondinellimorais/chess_recognition

systemd unit and execution settings:
https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html

uv Python environment management:
https://docs.astral.sh/uv/pip/environments/
