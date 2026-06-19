# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'unity_studio.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QSizePolicy, QTextBrowser, QVBoxLayout,
    QWidget)

from uitk.widgets.comboBox.ComboBox import ComboBox
from uitk.widgets.footer import Footer
from uitk.widgets.header import Header
from widgets.pushbutton import PushButton

class Ui_QtUi(object):
    def setupUi(self, QtUi):
        if not QtUi.objectName():
            QtUi.setObjectName(u"QtUi")
        QtUi.resize(360, 320)
        QtUi.setDockNestingEnabled(True)
        self.central_widget = QWidget(QtUi)
        self.central_widget.setObjectName(u"central_widget")
        self.central_widget.setMinimumSize(QSize(360, 0))
        self.verticalLayout_2 = QVBoxLayout(self.central_widget)
        self.verticalLayout_2.setSpacing(2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(2, 2, 2, 2)
        self.header = Header(self.central_widget)
        self.header.setObjectName(u"header")
        self.header.setMinimumSize(QSize(0, 19))
        self.header.setMaximumSize(QSize(16777215, 19))
        font = QFont()
        font.setBold(True)
        self.header.setFont(font)

        self.verticalLayout_2.addWidget(self.header)

        self.row_version = QHBoxLayout()
        self.row_version.setSpacing(2)
        self.row_version.setObjectName(u"row_version")
        self.lbl_version = QLabel(self.central_widget)
        self.lbl_version.setObjectName(u"lbl_version")
        self.lbl_version.setMinimumSize(QSize(90, 0))
        self.lbl_version.setAlignment(Qt.AlignRight|Qt.AlignVCenter)

        self.row_version.addWidget(self.lbl_version)

        self.cmb000 = ComboBox(self.central_widget)
        self.cmb000.setObjectName(u"cmb000")
        self.cmb000.setMinimumSize(QSize(0, 19))

        self.row_version.addWidget(self.cmb000)


        self.verticalLayout_2.addLayout(self.row_version)

        self.row_project = QHBoxLayout()
        self.row_project.setSpacing(2)
        self.row_project.setObjectName(u"row_project")
        self.lbl_project = QLabel(self.central_widget)
        self.lbl_project.setObjectName(u"lbl_project")
        self.lbl_project.setMinimumSize(QSize(90, 0))
        self.lbl_project.setAlignment(Qt.AlignRight|Qt.AlignVCenter)

        self.row_project.addWidget(self.lbl_project)

        self.project_field = QLineEdit(self.central_widget)
        self.project_field.setObjectName(u"project_field")
        self.project_field.setMinimumSize(QSize(0, 19))

        self.row_project.addWidget(self.project_field)

        self.b010 = PushButton(self.central_widget)
        self.b010.setObjectName(u"b010")
        self.b010.setMinimumSize(QSize(24, 19))
        self.b010.setMaximumSize(QSize(24, 19))

        self.row_project.addWidget(self.b010)


        self.verticalLayout_2.addLayout(self.row_project)

        self.row_recent = QHBoxLayout()
        self.row_recent.setSpacing(2)
        self.row_recent.setObjectName(u"row_recent")
        self.lbl_recent = QLabel(self.central_widget)
        self.lbl_recent.setObjectName(u"lbl_recent")
        self.lbl_recent.setMinimumSize(QSize(90, 0))
        self.lbl_recent.setAlignment(Qt.AlignRight|Qt.AlignVCenter)

        self.row_recent.addWidget(self.lbl_recent)

        self.cmb001 = ComboBox(self.central_widget)
        self.cmb001.setObjectName(u"cmb001")
        self.cmb001.setMinimumSize(QSize(0, 19))

        self.row_recent.addWidget(self.cmb001)


        self.verticalLayout_2.addLayout(self.row_recent)

        self.b000 = PushButton(self.central_widget)
        self.b000.setObjectName(u"b000")
        self.b000.setMinimumSize(QSize(0, 38))
        self.b000.setMaximumSize(QSize(16777215, 38))

        self.verticalLayout_2.addWidget(self.b000)

        self.b001 = PushButton(self.central_widget)
        self.b001.setObjectName(u"b001")
        self.b001.setMinimumSize(QSize(0, 22))
        self.b001.setMaximumSize(QSize(16777215, 22))

        self.verticalLayout_2.addWidget(self.b001)

        self.txt000 = QTextBrowser(self.central_widget)
        self.txt000.setObjectName(u"txt000")
        self.txt000.setMinimumSize(QSize(0, 110))
        self.txt000.setOpenLinks(False)
        self.txt000.setOpenExternalLinks(False)

        self.verticalLayout_2.addWidget(self.txt000)

        self.footer = Footer(self.central_widget)
        self.footer.setObjectName(u"footer")
        self.footer.setMinimumSize(QSize(0, 19))
        self.footer.setMaximumSize(QSize(16777215, 19))

        self.verticalLayout_2.addWidget(self.footer)

        QtUi.setCentralWidget(self.central_widget)

        self.retranslateUi(QtUi)

        QMetaObject.connectSlotsByName(QtUi)
    # setupUi

    def retranslateUi(self, QtUi):
        self.header.setText(QCoreApplication.translate("QtUi", u"UNITY STUDIO", None))
        self.lbl_version.setText(QCoreApplication.translate("QtUi", u"Unity Version:", None))
#if QT_CONFIG(tooltip)
        self.cmb000.setToolTip(QCoreApplication.translate("QtUi", u"Installed Unity Editors (auto-detected via Unity Hub). Newest is selected by default.", None))
#endif // QT_CONFIG(tooltip)
        self.lbl_project.setText(QCoreApplication.translate("QtUi", u"Project:", None))
#if QT_CONFIG(tooltip)
        self.project_field.setToolTip(QCoreApplication.translate("QtUi", u"The Unity project folder (the one containing Assets/).", None))
#endif // QT_CONFIG(tooltip)
        self.project_field.setPlaceholderText(QCoreApplication.translate("QtUi", u"(folder containing Assets/)", None))
#if QT_CONFIG(tooltip)
        self.b010.setToolTip(QCoreApplication.translate("QtUi", u"Browse for an existing Unity project folder.", None))
#endif // QT_CONFIG(tooltip)
        self.b010.setText(QCoreApplication.translate("QtUi", u"...", None))
        self.lbl_recent.setText(QCoreApplication.translate("QtUi", u"Recent:", None))
#if QT_CONFIG(tooltip)
        self.cmb001.setToolTip(QCoreApplication.translate("QtUi", u"Recently used projects. Selecting one fills the Project field.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.b000.setToolTip(QCoreApplication.translate("QtUi", u"Launch the selected Unity Editor on the chosen project.", None))
#endif // QT_CONFIG(tooltip)
        self.b000.setText(QCoreApplication.translate("QtUi", u"Launch Editor", None))
#if QT_CONFIG(tooltip)
        self.b001.setToolTip(QCoreApplication.translate("QtUi", u"Create a new Unity project with the selected Editor.", None))
#endif // QT_CONFIG(tooltip)
        self.b001.setText(QCoreApplication.translate("QtUi", u"New Project\u2026", None))
#if QT_CONFIG(tooltip)
        self.txt000.setToolTip(QCoreApplication.translate("QtUi", u"Launcher log.", None))
#endif // QT_CONFIG(tooltip)
        pass
    # retranslateUi

