import os
import sys
import zipfile

def export_zip(target_type="bot", out_file="/tmp/gln-bot.zip"):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Exclude heavy or sensitive directories and files
    excluded_dirs = {
        'node_modules',
        'python_modules',
        '.git',
        'dist',
        'build',
        'coverage',
        '__pycache__',
        '.vite',
        '.next'
    }
    
    excluded_extensions = ('.pyc', '.pyo', '.pyd', '.log', '.db', '.sqlite3')
    
    with zipfile.ZipFile(out_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(base_dir):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in excluded_dirs and not d.startswith('.')]
            
            for file in files:
                if file.endswith(excluded_extensions) or file.startswith('.'):
                    # Include .env, .env.example, and .gitignore
                    if file not in ('.env', '.env.example', '.gitignore'):
                        continue
                
                rel_path = os.path.relpath(os.path.join(root, file), base_dir)
                
                # If target_type is 'bot', only include Python bot files and general root configs
                if target_type == "bot":
                    if rel_path.startswith('src') or file in ('vite.config.ts', 'tsconfig.json', 'bun.lock', 'index.html'):
                        continue
                
                zf.write(os.path.join(root, file), arcname=rel_path)
    
    print(f"Zip created successfully at {out_file}, size: {os.path.getsize(out_file)} bytes")

if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else "bot"
    out = sys.argv[2] if len(sys.argv) > 2 else f"/tmp/gln-{t}.zip"
    export_zip(t, out)
