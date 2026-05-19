# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'mesh_convert.ui'
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
from PySide6.QtWidgets import (QApplication, QGroupBox, QLayout, QMainWindow,
    QSizePolicy, QSpacerItem, QTabWidget, QVBoxLayout,
    QWidget)

from uitk.widgets.collapsableGroup.CollapsableGroup import CollapsableGroup
from uitk.widgets.footer import Footer
from uitk.widgets.header import Header
from uitk.widgets.pushButton import PushButton

class Ui_QtUi(object):
    def setupUi(self, QtUi):
        if not QtUi.objectName():
            QtUi.setObjectName(u"QtUi")
        QtUi.resize(200, 110)
        QtUi.setTabShape(QTabWidget.Triangular)
        QtUi.setDockNestingEnabled(True)
        QtUi.setDockOptions(QMainWindow.AllowNestedDocks|QMainWindow.AllowTabbedDocks|QMainWindow.AnimatedDocks|QMainWindow.ForceTabbedDocks)
        self.central_widget = QWidget(QtUi)
        self.central_widget.setObjectName(u"central_widget")
        self.central_widget.setMinimumSize(QSize(200, 0))
        self.verticalLayout = QVBoxLayout(self.central_widget)
        self.verticalLayout.setSpacing(2)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(2, 2, 2, 2)
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(6)
        self.main_layout.setObjectName(u"main_layout")
        self.main_layout.setSizeConstraint(QLayout.SetFixedSize)
        self.header = Header(self.central_widget)
        self.header.setObjectName(u"header")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.header.sizePolicy().hasHeightForWidth())
        self.header.setSizePolicy(sizePolicy)
        self.header.setMinimumSize(QSize(0, 19))
        self.header.setMaximumSize(QSize(999, 19))
        font = QFont()
        font.setBold(True)
        self.header.setFont(font)

        self.main_layout.addWidget(self.header)

        self.Convert_group = QGroupBox(self.central_widget)
        self.Convert_group.setObjectName(u"Convert_group")
        self.verticalLayout_2 = QVBoxLayout(self.Convert_group)
        self.verticalLayout_2.setSpacing(1)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.groupBox_convert = CollapsableGroup(self.Convert_group)
        self.groupBox_convert.setObjectName(u"groupBox_convert")
        self.verticalLayout_3 = QVBoxLayout(self.groupBox_convert)
        self.verticalLayout_3.setSpacing(1)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(1, 1, 1, 1)
        self.tb000 = PushButton(self.groupBox_convert)
        self.tb000.setObjectName(u"tb000")
        self.tb000.setEnabled(True)
        sizePolicy.setHeightForWidth(self.tb000.sizePolicy().hasHeightForWidth())
        self.tb000.setSizePolicy(sizePolicy)
        self.tb000.setMinimumSize(QSize(0, 19))
        self.tb000.setMaximumSize(QSize(16777215, 19))

        self.verticalLayout_3.addWidget(self.tb000)


        self.verticalLayout_2.addWidget(self.groupBox_convert)


        self.main_layout.addWidget(self.Convert_group)

        self.verticalSpacer = QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.main_layout.addItem(self.verticalSpacer)

        self.footer = Footer(self.central_widget)
        self.footer.setObjectName(u"footer")
        self.footer.setMinimumSize(QSize(0, 19))
        self.footer.setMaximumSize(QSize(16777215, 19))

        self.main_layout.addWidget(self.footer)


        self.verticalLayout.addLayout(self.main_layout)

        QtUi.setCentralWidget(self.central_widget)

        self.retranslateUi(QtUi)

        QMetaObject.connectSlotsByName(QtUi)
    # setupUi

    def retranslateUi(self, QtUi):
        self.header.setText(QCoreApplication.translate("QtUi", u"MESH CONVERTER", None))
        self.Convert_group.setTitle("")
        self.groupBox_convert.setTitle(QCoreApplication.translate("QtUi", u"Convert:", None))
#if QT_CONFIG(tooltip)
        self.tb000.setToolTip(QCoreApplication.translate("QtUi", u"<b>Convert FBX to GLB</b><br>\n"
"Convert one or more FBX files to binary glTF 2.0 (GLB) using the godotengine/FBX2glTF CLI.<br><br>\n"
"<b>Usage:</b> Click to choose FBX files. Each is written next to the source as <i><name>.glb</i>.<br><br>\n"
"- <b>First-run:</b> the FBX2glTF binary (a few MB) is downloaded into <i>~/.pythontk/tools/</i>.<br>\n"
"- Use the option box for <b>Draco</b> compression and <b>Overwrite</b> behavior.", None))
#endif // QT_CONFIG(tooltip)
        self.tb000.setText(QCoreApplication.translate("QtUi", u"FBX to GLB", None))
        pass
    # retranslateUi

