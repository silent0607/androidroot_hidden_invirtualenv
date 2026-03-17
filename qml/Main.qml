import QtQuick 2.7
import Lomiri.Components 1.3
import io.thp.pyotherside 1.4
import Lomiri.Components.Popups 1.3

MainView {
    id: root
    objectName: "mainView"
    applicationName: "waydroid-wrapper.waydroid"
    
    width: units.gu(45)
    height: units.gu(75)

    property bool isPasswordNumeric: false
    property var inputMethodHints: null
    property string statusText: i18n.tr("Ready to start Waydroid")
    property bool isWorking: false
    property bool success: false

    Page {
        id: mainPage
        header: PageHeader {
            id: header
            title: i18n.tr("Waydroid Wrapper v1.3.35")
        }

        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#1a1a1a" }
                GradientStop { position: 1.0; color: "#0d0d0d" }
            }

            Column {
                anchors.centerIn: parent
                spacing: units.gu(4)
                width: parent.width * 0.8

                Image {
                    source: "../assets/logo.png"
                    width: units.gu(15)
                    height: units.gu(15)
                    anchors.horizontalCenter: parent.horizontalCenter
                    fillMode: Image.PreserveAspectFit
                }

                Label {
                    text: statusText
                    anchors.horizontalCenter: parent.horizontalCenter
                    color: success ? "#4CAF50" : "white"
                    font.pixelSize: units.gu(2)
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    width: parent.width
                }

                ActivityIndicator {
                    running: isWorking
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: isWorking
                }

                Button {
                    id: startButton
                    text: i18n.tr("Start Spoofed Waydroid")
                    width: parent.width
                    height: units.gu(6)
                    color: "#673AB7"
                    enabled: !isWorking
                    opacity: enabled ? 1.0 : 0.5
                    onClicked: {
                        PopupUtils.open(passPromptComp)
                    }
                }

                Button {
                    text: i18n.tr("Launch Waydroid UI")
                    width: parent.width
                    height: units.gu(6)
                    color: "#f39c12" // Orange
                    visible: success
                    enabled: !isWorking
                    onClicked: {
                        python.call('wrapper.start_ui', []);
                    }
                }
            }
        }
    }

    Component {
        id: passPromptComp
        Dialog {
            id: passPrompt
            title: i18n.tr("Root Authorization")

            TextField {
                id: passwordField
                placeholderText: i18n.tr("Sudo password")
                echoMode: TextInput.Password
                inputMethodHints: root.inputMethodHints
                width: parent.width
                
                onAccepted: startAction()
            }

            Button {
                text: i18n.tr("Cancel")
                onClicked: PopupUtils.close(passPrompt)
            }

            Button {
                text: i18n.tr("Authorize & Start")
                color: LomiriColors.purple
                onClicked: startAction()
            }

            function startAction() {
                isWorking = true;
                statusText = i18n.tr("Authorizing...");
                python.call('wrapper.start_spoofed_waydroid', [passwordField.text.trim()]);
                PopupUtils.close(passPrompt);
            }
        }
    }

    Python {
        id: python
        Component.onCompleted: {
            addImportPath(Qt.resolvedUrl('../src/'));
            importNames('main', ['wrapper'], function() {
                console.log('Main module and wrapper loaded');
            });
        }

        onReceived: {
            var data = arguments[0];
            
            // Handle both positional and list-wrapped signals
            var cmd, msg, done;
            if (typeof data === 'string') {
                cmd = arguments[0];
                msg = arguments[1];
                done = arguments[2];
            } else if (Array.isArray(data)) {
                cmd = data[0];
                msg = data[1];
                done = data[2];
            }

            if (cmd === 'status') {
                statusText = msg;
                if (done) {
                    success = true;
                    isWorking = false;
                }
            } else if (cmd === 'error') {
                statusText = "Error: " + msg;
                isWorking = false;
                success = false;
            }
        }

        onError: {
            statusText = "Python Error: " + traceback;
            isWorking = false;
            success = false;
        }
    }
}
