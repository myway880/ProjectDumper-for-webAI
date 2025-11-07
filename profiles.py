# profiles.py
# --- Default Profiles Section ---
# Default profiles extracted from core_dump.py for easier maintenance and development.
# This allows updating profiles without touching core logic, and potentially loading from external sources in future.
default_profiles = {
    "Custom": {
        "Extensions": [".js", ".ts", ".jsx", ".tsx", ".html", ".htm", ".svelte", ".vue", ".json", ".css", ".xml", ".cs", ".xaml", ".csproj", ".sln", ".bat"],
        "Exclude": [
            "node_modules/**", ".vscode/**", "static/**", "public/**", ".svelte-kit/**",
            ".git/**", "dist/**", "build/**", "**/*.log", "dump-config.json", "**/project-dump*.md", "**/project-dump*.txt",
            ".backup/**", "docs/**", "example/**", "tests/**", "vcpkg/**", "include/**", "**/.dump-project.json", ".**/**"
        ],
        "IncludePatterns": [],
        "ConfigFiles": []
    },
    "Web Dev": {
        "Extensions": [".js", ".ts", ".jsx", ".tsx", ".html", ".htm", ".svelte", ".vue", ".json", ".css", ".xml"],
        "Exclude": [
            "node_modules/**", "static/**", "public/**", ".svelte-kit/**", ".git/**", "dist/**", "build/**", "**/*.log",
            "dump-config.json", "**/project-dump*.md", "**/project-dump*.txt", ".backup/**", "docs/**", "example/**",
            "tests/**", "**/.dump-project.json", ".**/**"
        ],
        "IncludePatterns": [],
        "ConfigFiles": [".gitignore", "**.config.js", "package.json", "package-lock.json", "tsconfig.json", "**.config.js", "**.config.cjs", "postcss.config.cjs"]
    },
    "C/CPP Dev": {
        "Extensions": [".c", ".cpp", ".h", ".hpp", ".def", ".rc", ".rc2", ".vcxproj", ".filters", ".sln", ".in", ".build", ".tmpl"],
        "Exclude": [
            ".git/**", "dist/**", "build/**", "**/*.log", "dump-config.json", "**/project-dump*.**",
            ".backup/**", "docs/**", "example/**", "tests/**", "vcpkg/**", "**/.dump-project.json", ".**/**"
        ],
        "IncludePatterns": ["CMakeLists.txt", "Makefile", "makefile"],
        "ConfigFiles": ["vcpkg.json", "CMakeLists.txt", "build.bat", "install_vcpkg.bat", "**/*.vcxproj", "*.sln", "install-deps.ps1", "Makefile", "makefile"]
    },
    "Python Dev": {
        "Extensions": [".py", ".pyi", ".pyc", ".pyd", ".pyo", ".pyw", ".pyx", ".pxd", ".pxi", ".pyp", ".toml", ".ini", ".cfg", ".yaml", ".yml"],
        "Exclude": [
            "__pycache__/**", "*.egg-info/**", ".git/**", "dist/**", "build/**", "**/*.log", "dump-config.json", "**/project-dump*.**",
            ".backup/**", "docs/**", "example/**", "tests/**", "**/.dump-project.json", ".**/**"
        ],
        "IncludePatterns": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile", "tox.ini", "setup.cfg"],
        "ConfigFiles": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile", "tox.ini", "setup.cfg", ".pylintrc", "mypy.ini", "MANIFEST.in"]
    },
    "Java Dev": {
        "Extensions": [".java", ".jar", ".class", ".xml", ".gradle", ".properties"],
        "Exclude": [
            "target/**", ".gradle/**", ".git/**", "dist/**", "build/**", "**/*.log", "dump-config.json", "**/project-dump*.**",
            ".backup/**", "docs/**", "example/**", "tests/**", "**/.dump-project.json", ".**/**"
        ],
        "IncludePatterns": ["pom.xml", "build.gradle", "settings.gradle", "gradle.properties"],
        "ConfigFiles": ["pom.xml", "build.gradle", "settings.gradle", "gradle.properties", ".classpath", ".project", "build.xml"]
    },
    "Rust Dev": {
        "Extensions": [".rs", ".toml"],
        "Exclude": [
            "target/**", ".git/**", "dist/**", "build/**", "**/*.log", "dump-config.json", "**/project-dump*.**",
            ".backup/**", "docs/**", "example/**", "tests/**", "**/.dump-project.json", ".**/**"
        ],
        "IncludePatterns": ["Cargo.toml", "Cargo.lock"],
        "ConfigFiles": ["Cargo.toml", "Cargo.lock", "rustfmt.toml", "clippy.toml", "build.rs"]
    },
    "Go Dev": {
        "Extensions": [".go", ".mod", ".sum"],
        "Exclude": [
            "bin/**", "pkg/**", ".git/**", "dist/**", "build/**", "**/*.log", "dump-config.json", "**/project-dump*.**",
            ".backup/**", "docs/**", "example/**", "tests/**", "**/.dump-project.json", ".**/**"
        ],
        "IncludePatterns": ["go.mod", "go.sum", "go.work"],
        "ConfigFiles": ["go.mod", "go.sum", "go.work"]
    },
    "Ruby Dev": {
        "Extensions": [".rb", ".gemspec", ".ru"],
        "Exclude": [
            "vendor/**", ".git/**", "dist/**", "build/**", "**/*.log", "dump-config.json", "**/project-dump*.**",
            ".backup/**", "docs/**", "example/**", "tests/**", "**/.dump-project.json", ".**/**"
        ],
        "IncludePatterns": ["Gemfile", "Gemfile.lock", ".gemspec", "config.ru"],
        "ConfigFiles": ["Gemfile", "Gemfile.lock", ".gemspec", "config.ru", ".ruby-version"]
    },
    "PHP Dev": {
        "Extensions": [".php", ".json", ".lock", ".xml", ".env", ".ini"],
        "Exclude": [
            "vendor/**", ".git/**", "dist/**", "build/**", "**/*.log", "dump-config.json", "**/project-dump*.**",
            ".backup/**", "docs/**", "example/**", "tests/**", "**/.dump-project.json", ".**/**"
        ],
        "IncludePatterns": ["composer.json", "composer.lock", "phpunit.xml", ".env"],
        "ConfigFiles": ["composer.json", "composer.lock", "phpunit.xml", ".env", "php.ini"]
    },
    ".NET Dev": {
        "Extensions": [".cs", ".csproj", ".sln", ".vbproj", ".fsproj", ".json", ".config", ".xml"],
        "Exclude": [
            "bin/**", "obj/**", ".git/**", "dist/**", "build/**", "**/*.log", "dump-config.json", "**/project-dump*.**",
            ".backup/**", "docs/**", "example/**", "tests/**", "**/.dump-project.json", ".**/**"
        ],
        "IncludePatterns": ["appsettings.json", "*.csproj", "*.sln", "web.config", "NuGet.config"],
        "ConfigFiles": ["appsettings.json", "*.csproj", "*.sln", "web.config", "NuGet.config"]
    },
    "Android Dev": {
        "Extensions": [".java", ".kt", ".xml", ".gradle", ".properties"],
        "Exclude": [
            "build/**", ".gradle/**", ".git/**", "dist/**", "**/*.log", "dump-config.json", "**/project-dump*.**",
            ".backup/**", "docs/**", "example/**", "tests/**", "**/.dump-project.json", ".**/**"
        ],
        "IncludePatterns": ["build.gradle", "settings.gradle", "AndroidManifest.xml", "local.properties", "proguard-rules.pro"],
        "ConfigFiles": ["build.gradle", "settings.gradle", "AndroidManifest.xml", "local.properties", "proguard-rules.pro"]
    },
    "iOS Dev": {
        "Extensions": [".swift", ".xcconfig", ".plist", ".xcproject", ".xcworkspace"],
        "Exclude": [
            "build/**", ".git/**", "dist/**", "**/*.log", "dump-config.json", "**/project-dump*.**",
            ".backup/**", "docs/**", "example/**", "tests/**", "**/.dump-project.json", ".**/**"
        ],
        "IncludePatterns": ["*.xcconfig", "Podfile", "Podfile.lock", "Info.plist"],
        "ConfigFiles": ["*.xcconfig", "Podfile", "Podfile.lock", "Info.plist"]
    },
    "DevOps": {
        "Extensions": [".yml", ".yaml", ".groovy"],
        "Exclude": [
            ".git/**", "dist/**", "build/**", "**/*.log", "dump-config.json", "**/project-dump*.**",
            ".backup/**", "docs/**", "example/**", "tests/**", "**/.dump-project.json", ".**/**"
        ],
        "IncludePatterns": [".gitlab-ci.yml", ".github/workflows/*.yml", "Jenkinsfile", ".circleci/config.yml", ".travis.yml", "Dockerfile", "docker-compose.*", ".dockerignore"],
        "ConfigFiles": [".gitlab-ci.yml", ".github/workflows/*.yml", "Jenkinsfile", ".circleci/config.yml", ".travis.yml", "Dockerfile", "docker-compose.*", ".dockerignore"]
    }
}
# TODO (Enhancement): Add more profiles for additional languages or frameworks (e.g., Flutter, React Native).
# TODO (Design Improvement): Allow dynamic loading of profiles from user-defined JSON files.