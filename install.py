import os, sys
import platform
import subprocess
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

ascii_logo = """
__     ___     _            _     _                    
\ \   / (_) __| | ___  ___ | |   (_)_ __   __ _  ___  
 \ \ / /| |/ _` |/ _ \/ _ \| |   | | '_ \ / _` |/ _ \ 
  \ V / | | (_| |  __/ (_) | |___| | | | | (_| | (_) |
   \_/  |_|\__,_|\___|\___/|_____|_|_| |_|\__, |\___/ 
                                          |___/        
"""

def install_package(*packages):
    subprocess.check_call([sys.executable, "-m", "pip", "install", *packages])

def check_nvidia_gpu():
    install_package("pynvml")
    import pynvml
    from translations.translations import translate as t
    initialized = False
    try:
        pynvml.nvmlInit()
        initialized = True
        device_count = pynvml.nvmlDeviceGetCount()
        if device_count > 0:
            print(t("Detected NVIDIA GPU(s)"))
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                print(f"GPU {i}: {name}")
            return True
        else:
            print(t("No NVIDIA GPU detected"))
            return False
    except pynvml.NVMLError:
        print(t("No NVIDIA GPU detected or NVIDIA drivers not properly installed"))
        return False
    finally:
        if initialized:
            pynvml.nvmlShutdown()

def check_ffmpeg():
    from rich.console import Console
    from rich.panel import Panel
    from translations.translations import translate as t
    console = Console()

    try:
        # Check if ffmpeg is installed
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        console.print(Panel(t("✅ FFmpeg is already installed"), style="green"))
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        system = platform.system()
        install_cmd = ""
        
        if system == "Windows":
            install_cmd = "choco install ffmpeg"
            extra_note = t("Install Chocolatey first (https://chocolatey.org/)")
        elif system == "Darwin":
            install_cmd = "brew install ffmpeg"
            extra_note = t("Install Homebrew first (https://brew.sh/)")
        elif system == "Linux":
            install_cmd = "sudo apt install ffmpeg  # Ubuntu/Debian\nsudo yum install ffmpeg  # CentOS/RHEL"
            extra_note = t("Use your distribution's package manager")
        
        console.print(Panel.fit(
            t("⚠️ FFmpeg not found in PATH\n\n") +
            f"{t('🛠️ Install using:')}\n[bold cyan]{install_cmd}[/bold cyan]\n\n" +
            f"{t('💡 Note:')}\n{extra_note}\n\n" +
            f"{t('🔄 Continuing installation, but FFmpeg may be required for video processing')}\n",
            style="yellow"
        ))
        console.print(Panel("⚠️ FFmpeg not detected, but continuing installation...", style="yellow"))
        return False

def main():
    install_package("requests", "rich", "ruamel.yaml", "InquirerPy")
    from rich.console import Console
    from rich.panel import Panel
    from rich.box import DOUBLE
    from InquirerPy import inquirer
    from translations.translations import translate as t
    from translations.translations import DISPLAY_LANGUAGES
    from core.utils.config_utils import load_key, update_key
    from core.utils.decorator import except_handler

    console = Console()
    
    width = max(len(line) for line in ascii_logo.splitlines()) + 4
    welcome_panel = Panel(
        ascii_logo,
        width=width,
        box=DOUBLE,
        title="[bold green]🌏[/bold green]",
        border_style="bright_blue"
    )
    console.print(welcome_panel)
    # Language selection - Default to Chinese
    current_language = load_key("display_language")
    if not current_language:
        # Set default to Chinese
        selected_language = "zh-CN"
        update_key("display_language", selected_language)
        console.print(Panel(f"🌏 默认语言设置为中文 / Default language set to Chinese", style="cyan"))
    else:
        selected_language = current_language

    console.print(Panel.fit(t("🚀 Starting Installation"), style="bold magenta"))

    # Configure mirrors - Default to international PyPI
    console.print(Panel(t("🌍 Using international PyPI mirrors (default)"), style="cyan"))
    # Skip mirror configuration to use default international mirrors

    # Detect system and GPU
    has_gpu = platform.system() != 'Darwin' and check_nvidia_gpu()
    if has_gpu:
        console.print(Panel(t("🎮 NVIDIA GPU detected, installing CUDA version of PyTorch..."), style="cyan"))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "torch==2.0.0", "torchaudio==2.0.0", "--index-url", "https://download.pytorch.org/whl/cu118"])
    else:
        system_name = "🍎 MacOS" if platform.system() == 'Darwin' else "💻 No NVIDIA GPU"
        console.print(Panel(t(f"{system_name} detected, installing CPU version of PyTorch... Note: it might be slow during whisperX transcription."), style="cyan"))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "torch==2.1.2", "torchaudio==2.1.2"])

    @except_handler("Failed to install project")
    def install_requirements():
        console.print(Panel(t("Installing project in editable mode using `pip install -e .`"), style="cyan"))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."], env={**os.environ, "PIP_NO_CACHE_DIR": "0", "PYTHONIOENCODING": "utf-8"})

    @except_handler("Failed to install Noto fonts")
    def install_noto_font():
        # Skip font installation in containerized environments
        if os.environ.get("MODAL_ENVIRONMENT") or os.path.exists("/.dockerenv"):
            console.print("🐳 Container environment detected, skipping system font installation", style="cyan")
            return
            
        # Detect Linux distribution type
        if os.path.exists('/etc/debian_version'):
            # Debian/Ubuntu systems - without sudo
            cmd = ['apt-get', 'install', '-y', 'fonts-noto']
            pkg_manager = "apt-get"
        elif os.path.exists('/etc/redhat-release'):
            # RHEL/CentOS/Fedora systems - without sudo
            cmd = ['yum', 'install', '-y', 'google-noto*']
            pkg_manager = "yum"
        else:
            console.print("Warning: Unrecognized Linux distribution, skipping Noto fonts installation", style="yellow")
            return

        try:
            subprocess.run(cmd, check=True)
            console.print(f"✅ Successfully installed Noto fonts using {pkg_manager}", style="green")
        except subprocess.CalledProcessError:
            console.print(f"⚠️ Could not install Noto fonts with {pkg_manager}, continuing without fonts", style="yellow")

    if platform.system() == 'Linux':
        install_noto_font()
    
    install_requirements()
    ffmpeg_available = check_ffmpeg()
    
    if not ffmpeg_available:
        console.print(Panel("⚠️ FFmpeg not found, but installation will continue. Video processing may not work properly.", style="yellow"))
    
    # First panel with installation complete and startup command
    panel1_text = (
        t("Installation completed") + "\n\n" +
        t("Now I will run this command to start the application:") + "\n" +
        "[bold]streamlit run st.py[/bold]\n" +
        t("Note: First startup may take up to 1 minute")
    )
    console.print(Panel(panel1_text, style="bold green"))

    # Second panel with troubleshooting tips
    panel2_text = (
        t("If the application fails to start:") + "\n" +
        "1. " + t("Check your network connection") + "\n" +
        "2. " + t("Re-run the installer: [bold]python install.py[/bold]")
    )
    console.print(Panel(panel2_text, style="yellow"))

    # Skip automatic startup in Modal environment or when port is already in use
    if (os.environ.get("MODAL_ENVIRONMENT") or 
        os.environ.get("STREAMLIT_SERVER_PORT") or 
        os.environ.get("MODAL_TASK_ID") or
        "modal" in os.getcwd().lower()):
        console.print(Panel("🏖️ Modal/Container environment detected, skipping automatic startup", style="cyan"))
        console.print(Panel("✅ Installation completed successfully! Streamlit will be started by the container.", style="green"))
    else:
        # start the application
        subprocess.Popen(["streamlit", "run", "st.py"])

if __name__ == "__main__":
    main()
