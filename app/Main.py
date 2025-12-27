
import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(
    page_title="EA1RFI Web",
    layout="wide",
)

st.title("📻 EA1RFI Personal Web")
st.subheader("My personal Ham Radio space")


st.markdown("""
Hello everyone! Welcome to EA1RFI's personal ham radio page!
            
My name is Daniel. I recently obtained my ham radio license (2025) after many years listening to radio emissions through an SDR device (RTL-SDR). 
I decided that it was time to get on the air! Since I was a child, I always loved to listen to the radio at night, and my parents gave me a SW radio that I still have. 
I found also that walkies were amazing and how I could talk with friends using them. As a child, even if they were only some few meters apart I found that to be pretty cool. 
I have a background in Telecommunications Engineering since 2010, which also helps that I'm here right now as I deeply understand the tech and maths behind radio communications.

Inside this web you will find some content that I'm developing. These are the tools right now:
            
- QSO Mapper and Stats. A tool that uses an ADI file to generate a map of the world with all your QSOs. You may download an HTML file with your map to use where you want. No logfile is stored so you can use it freely, I don't keep any data. I'm working also on a dashboard to see some interesting stats from your logfile. The code can be reached at https://github.com/dgarcoe/ea1rfi_qso_mapper and it is opensource with a MIT license (any contributions and feedback are welcomed!)
            
I'm eager to find you in the waves and make some HF contacts! 

73!
""")

components.iframe("https://logbook.qrz.com/lbstat/EA1RFI/", height=500)


