use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::Path;
use std::process::Command;
use regex::Regex;
use std::sync::LazyLock;

static ARCH_SUFFIX: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)[-_]?(?:x86_64|x86|x64|64|32|win64|win32|shipping)+$").unwrap()
});

static WINDOW_ID_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"0x[0-9a-fA-F]+").unwrap()
});

static PID_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"= (\d+)$").unwrap()
});

pub fn add_name(exes: &mut HashSet<String>, raw_name: &str) {
    let name = raw_name.trim().to_lowercase();
    if name.is_empty() {
        return;
    }
    exes.insert(name.clone());

    let has_exe = name.ends_with(".exe");
    let stem = if has_exe {
        name[..name.len() - 4].to_string()
    } else {
        name.clone()
    };
    exes.insert(stem.clone());

    let base = ARCH_SUFFIX.replace(&stem, "").to_string();
    if !base.is_empty() && base != stem {
        exes.insert(base.clone());
        exes.insert(format!("{}.exe", base));
    }

    if name.contains(' ') {
        exes.insert(name.replace(' ', ""));
        if has_exe {
            exes.insert(stem.replace(' ', ""));
        }
    }
}

pub fn basename_any_os(path: &str) -> String {
    let normalized = path.replace('\\', "/");
    normalized
        .rsplit('/')
        .next()
        .unwrap_or(path)
        .to_string()
}

pub fn is_flatpak() -> bool {
    Path::new("/.flatpak-info").exists()
}

pub fn scan_processes() -> HashMap<u32, HashSet<String>> {
    let mut procs: HashMap<u32, HashSet<String>> = HashMap::new();

    if is_flatpak() {
        let script = "import os, sys\n\
for entry in os.scandir('/proc'):\n\
    if not entry.name.isdigit(): continue\n\
    try:\n\
        exe = os.readlink(f'/proc/{entry.name}/exe')\n\
    except OSError:\n\
        exe = ''\n\
    try:\n\
        with open(f'/proc/{entry.name}/cmdline', 'rb') as f:\n\
            argv0 = f.read(4096).split(b'\\0', 1)[0].decode('utf-8', 'replace')\n\
    except OSError:\n\
        argv0 = ''\n\
    if exe or argv0:\n\
        sys.stdout.write(f'{entry.name}\\t{os.path.basename(exe)}\\t{argv0}\\n')";

        if let Ok(output) = Command::new("flatpak-spawn")
            .args(["--host", "python3", "-c", script])
            .output()
        {
            let stdout = String::from_utf8_lossy(&output.stdout);
            for line in stdout.lines() {
                let parts: Vec<&str> = line.split('\t').collect();
                if parts.len() >= 2 {
                    if let Ok(pid) = parts[0].parse::<u32>() {
                        let mut names = HashSet::new();
                        let exe_name = parts[1];
                        let argv0 = if parts.len() > 2 { parts[2] } else { "" };
                        if !exe_name.is_empty() {
                            add_name(&mut names, exe_name);
                        }
                        if !argv0.is_empty() {
                            add_name(&mut names, &basename_any_os(argv0));
                        }
                        if !names.is_empty() {
                            procs.insert(pid, names);
                        }
                    }
                }
            }
            return procs;
        }
    }

    let proc_dir = match fs::read_dir("/proc") {
        Ok(dir) => dir,
        Err(_) => return procs,
    };

    for entry in proc_dir.flatten() {
        let file_name = entry.file_name();
        let pid_str = match file_name.to_str() {
            Some(s) if s.chars().all(|c| c.is_ascii_digit()) => s,
            _ => continue,
        };

        let pid: u32 = match pid_str.parse() {
            Ok(p) => p,
            Err(_) => continue,
        };

        let mut names = HashSet::new();

        // 1. Check /proc/PID/exe (native binary symlink)
        let exe_path = Path::new("/proc").join(pid_str).join("exe");
        if let Ok(target) = fs::read_link(&exe_path) {
            if let Some(target_name) = target.file_name().and_then(|n| n.to_str()) {
                add_name(&mut names, target_name);
            }
        }

        // 2. Check /proc/PID/cmdline (argv[0], critical for Wine/Proton games)
        let cmdline_path = Path::new("/proc").join(pid_str).join("cmdline");
        if let Ok(bytes) = fs::read(&cmdline_path) {
            if let Some(first_arg) = bytes.split(|&b| b == 0).next() {
                if !first_arg.is_empty() {
                    let arg0 = String::from_utf8_lossy(first_arg);
                    add_name(&mut names, &basename_any_os(&arg0));
                }
            }
        }

        if !names.is_empty() {
            procs.insert(pid, names);
        }
    }

    procs
}

pub fn focused_pid() -> Option<u32> {
    let mut cmd = if is_flatpak() {
        let mut c = Command::new("flatpak-spawn");
        c.args(["--host", "xprop"]);
        c
    } else {
        Command::new("xprop")
    };

    let output = cmd
        .args(["-root", "_NET_ACTIVE_WINDOW"])
        .output()
        .ok()?;

    if output.status.success() {
        let stdout = String::from_utf8_lossy(&output.stdout);
        if let Some(win_match) = WINDOW_ID_RE.find(&stdout) {
            let win_id_str = win_match.as_str();
            let win_id = u64::from_str_radix(win_id_str.trim_start_matches("0x"), 16).unwrap_or(0);
            if win_id > 0 {
                let mut pid_cmd = if is_flatpak() {
                    let mut c = Command::new("flatpak-spawn");
                    c.args(["--host", "xprop"]);
                    c
                } else {
                    Command::new("xprop")
                };

                if let Ok(pid_output) = pid_cmd.args(["-id", win_id_str, "_NET_WM_PID"]).output() {
                    if pid_output.status.success() {
                        let pid_str = String::from_utf8_lossy(&pid_output.stdout);
                        if let Some(caps) = PID_RE.captures(pid_str.trim()) {
                            if let Some(pid) = caps.get(1).and_then(|m| m.as_str().parse::<u32>().ok()) {
                                if pid > 0 {
                                    return Some(pid);
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_name_aliases() {
        let mut names = HashSet::new();
        add_name(&mut names, "HeroesOfTheStorm_x64.exe");

        assert!(names.contains("heroesofthestorm_x64.exe"));
        assert!(names.contains("heroesofthestorm_x64"));
        assert!(names.contains("heroesofthestorm.exe"));
        assert!(names.contains("heroesofthestorm"));
    }

    #[test]
    fn test_add_name_spaces() {
        let mut names = HashSet::new();
        add_name(&mut names, "heroes of the storm.exe");

        assert!(names.contains("heroes of the storm.exe"));
        assert!(names.contains("heroes of the storm"));
        assert!(names.contains("heroesofthestorm.exe"));
        assert!(names.contains("heroesofthestorm"));
    }

    #[test]
    fn test_basename_any_os() {
        assert_eq!(
            basename_any_os(r"Z:\Games\Overwatch\Overwatch.exe"),
            "Overwatch.exe"
        );
        assert_eq!(
            basename_any_os("/usr/bin/disco.exe"),
            "disco.exe"
        );
    }
}
