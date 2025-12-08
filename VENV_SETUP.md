# Virtual Environment Setup Instructions

## Prerequisites
- Python 3.13 (or compatible version) installed
- VSCode with Python extension installed

---

## Initial Setup (Already Completed)

The virtual environment has already been created and configured for this project:
- ✅ Virtual environment created at `./venv/`
- ✅ Dependencies installed (PyQt5, PyYAML, qasync)
- ✅ VSCode settings configured
- ✅ `.gitignore` updated

---

## How to Activate the Virtual Environment

### Option 1: Activate in VSCode Terminal (Recommended)

1. **Open a new terminal in VSCode**:
   - Press `` Ctrl+` `` (backtick) or go to `Terminal → New Terminal`

2. **Activate the virtual environment**:
   ```bash
   source venv/bin/activate
   ```

3. **Verify activation**:
   - Your terminal prompt should now show `(venv)` at the beginning
   - Example: `(venv) jeremeshaver@Jeremes-MacBook-Pro Project-Meridian %`

4. **Verify Python is from venv**:
   ```bash
   which python
   ```
   - Should output: `/Users/jeremeshaver/Documents/GitHub/Project-Meridian/venv/bin/python`

5. **Run the application**:
   ```bash
   python main.py
   ```

---

### Option 2: Configure VSCode to Auto-Activate

VSCode has already been configured to automatically activate the venv, but you may need to reload:

1. **Reload VSCode Window**:
   - Press `Cmd+Shift+P`
   - Type "Developer: Reload Window"
   - Press Enter

2. **Open a new terminal**:
   - Press `` Ctrl+` ``
   - The venv should activate automatically (you'll see `(venv)` in the prompt)

---

### Option 3: Select Python Interpreter in VSCode

1. **Open Command Palette**:
   - Press `Cmd+Shift+P`

2. **Select Interpreter**:
   - Type "Python: Select Interpreter"
   - Choose `./venv/bin/python` (should show Python 3.13.x)

3. **Run or Debug**:
   - Use VSCode's Run/Debug buttons
   - The venv will be used automatically

---

## Deactivating the Virtual Environment

When you're done working:

```bash
deactivate
```

This will return you to the system Python environment.

---

## Troubleshooting

### Problem: "No module named 'yaml'" error

**Solution**: Make sure the venv is activated:
```bash
source venv/bin/activate
python main.py
```

### Problem: VSCode still using system Python

**Solution 1**: Reload the window
- `Cmd+Shift+P` → "Developer: Reload Window"

**Solution 2**: Manually select interpreter
- `Cmd+Shift+P` → "Python: Select Interpreter" → Choose `./venv/bin/python`

### Problem: Terminal doesn't show (venv)

**Solution**: Manually activate:
```bash
source venv/bin/activate
```

### Problem: Permission denied

**Solution**: Make sure the activate script is executable:
```bash
chmod +x venv/bin/activate
```

---

## Installing Additional Packages

If you need to install more Python packages:

1. **Activate the venv**:
   ```bash
   source venv/bin/activate
   ```

2. **Install package**:
   ```bash
   pip install package-name
   ```

3. **Update requirements.txt**:
   ```bash
   pip freeze > requirements.txt
   ```

---

## Recreating the Virtual Environment

If you need to start fresh:

1. **Delete the old venv**:
   ```bash
   rm -rf venv
   ```

2. **Create new venv**:
   ```bash
   python3 -m venv venv
   ```

3. **Activate it**:
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `source venv/bin/activate` | Activate virtual environment |
| `deactivate` | Deactivate virtual environment |
| `which python` | Check which Python is being used |
| `pip list` | Show installed packages |
| `pip install -r requirements.txt` | Install all dependencies |
| `python main.py` | Run the application |

---

## VSCode Configuration Files

The following files have been created/modified for venv support:

- `.vscode/settings.json` - Configures default Python interpreter
- `requirements.txt` - Lists project dependencies
- `.gitignore` - Excludes venv from version control

---

## Current Dependencies

```
PyQt5>=5.15.0
PyYAML>=6.0
qasync>=0.23.0
```

---

## Notes

- **Always activate the venv** before running the application or installing packages
- The venv is **local to this project** and doesn't affect your system Python
- **Don't commit** the `venv/` folder to git (it's already in `.gitignore`)
- If you move the project, you may need to recreate the venv
