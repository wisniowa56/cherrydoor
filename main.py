from cherrydoor import app, socket

if __name__ == "__main__":
    # app.run(debug=True)
    socket.run(app, log_output=True)
