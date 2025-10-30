# 🌍📻 EA1RFI QSO Mapper

A Streamlit app to map your QSOs from an ADIF file

## 📋 Main Features

### ✅ Implemented

- Map your QSOs in a world map from an ADIF file with gridsquares or latitude and longitude fields filled
- Paints the great circle lines from your QTH towards the QSO
- Uses different colours to represent different bands
- When hovering over the QSO you can see its details such as callsign, frequency, band, mode and grid
- Calculates the distance to the QSO, showing it also in the tooltip
- You can download your map in an HTML file and do with it what you want

### 🚧 Soon

- Show the country in the tooltip
- Allow to choose if great circles want to be painted or not
- Allow to choose from several map tiles
- Differentiate icons depending on the mode
- Show QSO stats in graphs

## 🚀 Basic setup

### ⚙️ Requirements

- Python **3.9 or superior**
- Recommended: virtual environment (`venv`)

---

### 🧩 Installation

1. **Clone the repo**
  
\`\`\`bash
git clone <repository-url>
cd dialysis-stock-management
\`\`\`

2. **Create and activate a virtual env (optional)**

\`\`\`bash
python -m venv venv
source venv/bin/activate
\`\`\`

3. **Install dependencies**

\`\`\`bash
pip install -r requirements.txt
\`\`\`

4. **Run the app**

\`\`\`bash
streamlit run app.py
\`\`\`   

Then open the link showing in the terminal (default: http://localhost:8501)


