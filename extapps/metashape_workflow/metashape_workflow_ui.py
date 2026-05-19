# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'metashape_workflow.ui'
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
from PySide6.QtWidgets import (QAbstractScrollArea, QApplication, QGroupBox, QHBoxLayout,
    QMainWindow, QPushButton, QSizePolicy, QTabWidget,
    QTextBrowser, QVBoxLayout, QWidget)

from uitk.widgets.collapsableGroup import CollapsableGroup
from uitk.widgets.comboBox import ComboBox
from uitk.widgets.footer import Footer
from uitk.widgets.header import Header
from uitk.widgets.lineEdit import LineEdit

class Ui_QtUi(object):
    def setupUi(self, QtUi):
        if not QtUi.objectName():
            QtUi.setObjectName(u"QtUi")
        QtUi.setEnabled(True)
        QtUi.resize(600, 411)
        QtUi.setTabShape(QTabWidget.Triangular)
        QtUi.setDockNestingEnabled(True)
        QtUi.setDockOptions(QMainWindow.AllowNestedDocks|QMainWindow.AllowTabbedDocks|QMainWindow.AnimatedDocks|QMainWindow.ForceTabbedDocks)
        self.central_widget = QWidget(QtUi)
        self.central_widget.setObjectName(u"central_widget")
        self.central_widget.setMinimumSize(QSize(600, 280))
        self.verticalLayout_2 = QVBoxLayout(self.central_widget)
        self.verticalLayout_2.setSpacing(2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(2, 2, 2, 2)
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(1)
        self.main_layout.setObjectName(u"main_layout")
        self.header = Header(self.central_widget)
        self.header.setObjectName(u"header")
        self.header.setMinimumSize(QSize(0, 19))
        font = QFont()
        font.setBold(True)
        self.header.setFont(font)

        self.main_layout.addWidget(self.header)

        self.File = QGroupBox(self.central_widget)
        self.File.setObjectName(u"File")
        self.File.setMinimumSize(QSize(0, 160))
        self.File.setMaximumSize(QSize(16777215, 160))
        self.verticalLayout_3 = QVBoxLayout(self.File)
        self.verticalLayout_3.setSpacing(1)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.txt000 = LineEdit(self.File)
        self.txt000.setObjectName(u"txt000")
        self.txt000.setMinimumSize(QSize(0, 19))
        self.txt000.setMaximumSize(QSize(16777215, 19))

        self.verticalLayout_3.addWidget(self.txt000)

        self.txt001 = LineEdit(self.File)
        self.txt001.setObjectName(u"txt001")
        self.txt001.setMinimumSize(QSize(0, 19))
        self.txt001.setMaximumSize(QSize(16777215, 19))

        self.verticalLayout_3.addWidget(self.txt001)

        self.txt002 = LineEdit(self.File)
        self.txt002.setObjectName(u"txt002")
        self.txt002.setMinimumSize(QSize(0, 19))
        self.txt002.setMaximumSize(QSize(16777215, 19))

        self.verticalLayout_3.addWidget(self.txt002)

        self.presets = QGroupBox(self.File)
        self.presets.setObjectName(u"presets")
        self.horizontalLayout_2 = QHBoxLayout(self.presets)
        self.horizontalLayout_2.setSpacing(1)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.cmb000 = ComboBox(self.presets)
        self.cmb000.setObjectName(u"cmb000")
        self.cmb000.setMinimumSize(QSize(0, 19))
        self.cmb000.setMaximumSize(QSize(16777215, 19))

        self.horizontalLayout_2.addWidget(self.cmb000)


        self.verticalLayout_3.addWidget(self.presets)

        self.layout_option_buttons = QHBoxLayout()
        self.layout_option_buttons.setSpacing(1)
        self.layout_option_buttons.setObjectName(u"layout_option_buttons")
        self.btn_stages = QPushButton(self.File)
        self.btn_stages.setObjectName(u"btn_stages")
        self.btn_stages.setMinimumSize(QSize(0, 19))
        self.btn_stages.setMaximumSize(QSize(16777215, 19))

        self.layout_option_buttons.addWidget(self.btn_stages)

        self.btn_advanced = QPushButton(self.File)
        self.btn_advanced.setObjectName(u"btn_advanced")
        self.btn_advanced.setMinimumSize(QSize(0, 19))
        self.btn_advanced.setMaximumSize(QSize(16777215, 19))

        self.layout_option_buttons.addWidget(self.btn_advanced)


        self.verticalLayout_3.addLayout(self.layout_option_buttons)

        self.b000 = QPushButton(self.File)
        self.b000.setObjectName(u"b000")
        self.b000.setMinimumSize(QSize(0, 38))
        self.b000.setMaximumSize(QSize(16777215, 38))

        self.verticalLayout_3.addWidget(self.b000)


        self.main_layout.addWidget(self.File)

        self.output = CollapsableGroup(self.central_widget)
        self.output.setObjectName(u"output")
        self.output.setFont(font)
        self.output.setAlignment(Qt.AlignCenter)
        self.verticalLayout_4 = QVBoxLayout(self.output)
        self.verticalLayout_4.setSpacing(1)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.txt003 = QTextBrowser(self.output)
        self.txt003.setObjectName(u"txt003")
        self.txt003.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.txt003.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.txt003.setOpenExternalLinks(False)
        self.txt003.setOpenLinks(False)

        self.verticalLayout_4.addWidget(self.txt003)


        self.main_layout.addWidget(self.output)

        self.footer = Footer(self.central_widget)
        self.footer.setObjectName(u"footer")
        self.footer.setMinimumSize(QSize(0, 19))
        self.footer.setMaximumSize(QSize(16777215, 19))

        self.main_layout.addWidget(self.footer)


        self.verticalLayout_2.addLayout(self.main_layout)

        QtUi.setCentralWidget(self.central_widget)

        self.retranslateUi(QtUi)

        QMetaObject.connectSlotsByName(QtUi)
    # setupUi

    def retranslateUi(self, QtUi):
        self.header.setText(QCoreApplication.translate("QtUi", u"METASHAPE WORKFLOW", None))
        self.File.setTitle("")
#if QT_CONFIG(tooltip)
        self.txt000.setToolTip(QCoreApplication.translate("QtUi", u"Directory where the Metashape project (.psx) and exported model will be saved.", None))
#endif // QT_CONFIG(tooltip)
        self.txt000.setPlaceholderText(QCoreApplication.translate("QtUi", u"Project Directory:", None))
#if QT_CONFIG(tooltip)
        self.txt001.setToolTip(QCoreApplication.translate("QtUi", u"Optional basename for the project and exported model. Defaults to the project directory name.", None))
#endif // QT_CONFIG(tooltip)
        self.txt001.setPlaceholderText(QCoreApplication.translate("QtUi", u"Project Name (optional):", None))
#if QT_CONFIG(tooltip)
        self.txt002.setToolTip(QCoreApplication.translate("QtUi", u"Folder containing the source images for photogrammetry.", None))
#endif // QT_CONFIG(tooltip)
        self.txt002.setPlaceholderText(QCoreApplication.translate("QtUi", u"Frames Directory:", None))
        self.presets.setTitle(QCoreApplication.translate("QtUi", u"Preset:", None))
#if QT_CONFIG(tooltip)
        self.cmb000.setToolTip(QCoreApplication.translate("QtUi", u"Quality preset. Controls alignment / depth downscale, face count, and texture size.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.btn_stages.setToolTip(QCoreApplication.translate("QtUi", u"Select which pipeline stages to run.", None))
#endif // QT_CONFIG(tooltip)
        self.btn_stages.setText(QCoreApplication.translate("QtUi", u"Pipeline Stages", None))
#if QT_CONFIG(tooltip)
        self.btn_advanced.setToolTip(QCoreApplication.translate("QtUi", u"Advanced parameters (texture size, face count, filters, frame-extraction step).", None))
#endif // QT_CONFIG(tooltip)
        self.btn_advanced.setText(QCoreApplication.translate("QtUi", u"Advanced", None))
        self.b000.setText(QCoreApplication.translate("QtUi", u"Run Workflow", None))
        self.output.setTitle(QCoreApplication.translate("QtUi", u"\u2022 \u2022 \u2022", None))
        pass
    # retranslateUi

