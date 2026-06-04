# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'marmoset_workflow.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGroupBox, QMainWindow,
    QSizePolicy, QTextBrowser, QVBoxLayout, QWidget)

from uitk.widgets.comboBox.ComboBox import ComboBox
from uitk.widgets.footer import Footer
from uitk.widgets.header import Header
from widgets.pushbutton import PushButton

class Ui_QtUi(object):
    def setupUi(self, QtUi):
        if not QtUi.objectName():
            QtUi.setObjectName(u"QtUi")
        QtUi.resize(340, 300)
        QtUi.setDockNestingEnabled(True)
        self.central_widget = QWidget(QtUi)
        self.central_widget.setObjectName(u"central_widget")
        self.central_widget.setMinimumSize(QSize(340, 0))
        self.verticalLayout_2 = QVBoxLayout(self.central_widget)
        self.verticalLayout_2.setSpacing(2)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(2, 2, 2, 2)
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.header = Header(self.central_widget)
        self.header.setObjectName(u"header")
        self.header.setMinimumSize(QSize(0, 19))
        self.header.setMaximumSize(QSize(16777215, 19))
        font = QFont()
        font.setBold(True)
        self.header.setFont(font)

        self.verticalLayout.addWidget(self.header)

        self.grp_process = QGroupBox(self.central_widget)
        self.grp_process.setObjectName(u"grp_process")
        self.verticalLayout_3 = QVBoxLayout(self.grp_process)
        self.verticalLayout_3.setSpacing(1)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.cmb000 = ComboBox(self.grp_process)
        self.cmb000.setObjectName(u"cmb000")
        self.cmb000.setMinimumSize(QSize(0, 19))
        self.cmb000.setMaximumSize(QSize(16777215, 19))
        self.cmb000.setMaxVisibleItems(40)
        self.cmb000.setMaxCount(500)
        self.cmb000.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.cmb000.setFrame(True)

        self.verticalLayout_3.addWidget(self.cmb000)

        self.b000 = PushButton(self.grp_process)
        self.b000.setObjectName(u"b000")
        self.b000.setMinimumSize(QSize(0, 38))
        self.b000.setMaximumSize(QSize(16777215, 38))

        self.verticalLayout_3.addWidget(self.b000)


        self.verticalLayout.addWidget(self.grp_process)

        self.txt000 = QTextBrowser(self.central_widget)
        self.txt000.setObjectName(u"txt000")
        self.txt000.setMinimumSize(QSize(0, 110))
        self.txt000.setOpenLinks(False)
        self.txt000.setOpenExternalLinks(False)

        self.verticalLayout.addWidget(self.txt000)

        self.footer = Footer(self.central_widget)
        self.footer.setObjectName(u"footer")
        self.footer.setMinimumSize(QSize(0, 19))
        self.footer.setMaximumSize(QSize(16777215, 19))

        self.verticalLayout.addWidget(self.footer)


        self.verticalLayout_2.addLayout(self.verticalLayout)

        QtUi.setCentralWidget(self.central_widget)

        self.retranslateUi(QtUi)

        QMetaObject.connectSlotsByName(QtUi)
    # setupUi

    def retranslateUi(self, QtUi):
        self.header.setText(QCoreApplication.translate("QtUi", u"MARMOSET WORKFLOW", None))
        self.grp_process.setTitle("")
#if QT_CONFIG(tooltip)
        self.cmb000.setToolTip(QCoreApplication.translate("QtUi", u"Pick how to set up the project in Toolbag (import = bare import, lookdev = sky + frame).", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.b000.setToolTip(QCoreApplication.translate("QtUi", u"Launch Marmoset Toolbag and set up a project from the chosen model file.", None))
#endif // QT_CONFIG(tooltip)
        self.b000.setText(QCoreApplication.translate("QtUi", u"Set Up in Marmoset", None))
#if QT_CONFIG(tooltip)
        self.txt000.setToolTip(QCoreApplication.translate("QtUi", u"Workflow log. Click linked paths to open them in the file explorer.", None))
#endif // QT_CONFIG(tooltip)
        pass
    # retranslateUi

