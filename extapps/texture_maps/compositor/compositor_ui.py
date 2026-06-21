# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'compositor.ui'
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
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QMainWindow,
    QSizePolicy, QTabWidget, QTextEdit, QVBoxLayout,
    QWidget)

from uitk.widgets.footer import Footer
from uitk.widgets.header import Header
from uitk.widgets.lineEdit import LineEdit

class Ui_QtUi(object):
    def setupUi(self, QtUi):
        if not QtUi.objectName():
            QtUi.setObjectName(u"QtUi")
        QtUi.setEnabled(True)
        QtUi.resize(750, 394)
        QtUi.setMinimumSize(QSize(750, 176))
        QtUi.setTabShape(QTabWidget.Triangular)
        QtUi.setDockNestingEnabled(True)
        QtUi.setDockOptions(QMainWindow.AllowNestedDocks|QMainWindow.AllowTabbedDocks|QMainWindow.AnimatedDocks|QMainWindow.ForceTabbedDocks)
        self.central_widget = QWidget(QtUi)
        self.central_widget.setObjectName(u"central_widget")
        self.gridLayout_2 = QGridLayout(self.central_widget)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setHorizontalSpacing(2)
        self.gridLayout_2.setVerticalSpacing(0)
        self.gridLayout_2.setContentsMargins(2, 2, 2, 2)
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(1)
        self.main_layout.setObjectName(u"main_layout")
        self.header = Header(self.central_widget)
        self.header.setObjectName(u"header")
        self.header.setMinimumSize(QSize(0, 19))
        self.header.setMaximumSize(QSize(16777215, 19))
        font = QFont()
        font.setBold(True)
        self.header.setFont(font)

        self.main_layout.addWidget(self.header)

        self.gridLayout = QGridLayout()
        self.gridLayout.setSpacing(1)
        self.gridLayout.setObjectName(u"gridLayout")
        self.txt000 = LineEdit(self.central_widget)
        self.txt000.setObjectName(u"txt000")
        self.txt000.setMinimumSize(QSize(0, 19))
        self.txt000.setMaximumSize(QSize(16777215, 19))

        self.gridLayout.addWidget(self.txt000, 4, 0, 1, 5)

        self.txt001 = LineEdit(self.central_widget)
        self.txt001.setObjectName(u"txt001")
        self.txt001.setMinimumSize(QSize(0, 19))
        self.txt001.setMaximumSize(QSize(16777215, 19))

        self.gridLayout.addWidget(self.txt001, 5, 0, 1, 5)

        self.txt002 = LineEdit(self.central_widget)
        self.txt002.setObjectName(u"txt002")
        self.txt002.setMinimumSize(QSize(0, 19))
        self.txt002.setMaximumSize(QSize(16777215, 19))

        self.gridLayout.addWidget(self.txt002, 6, 0, 1, 5)


        self.main_layout.addLayout(self.gridLayout)

        self.txt003 = QTextEdit(self.central_widget)
        self.txt003.setObjectName(u"txt003")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.txt003.sizePolicy().hasHeightForWidth())
        self.txt003.setSizePolicy(sizePolicy)
        self.txt003.setMinimumSize(QSize(0, 300))
        self.txt003.setFrameShape(QFrame.NoFrame)
        self.txt003.setFrameShadow(QFrame.Plain)
        self.txt003.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.txt003.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.txt003.setReadOnly(True)

        self.main_layout.addWidget(self.txt003)

        self.footer = Footer(self.central_widget)
        self.footer.setObjectName(u"footer")
        self.footer.setMinimumSize(QSize(0, 19))
        self.footer.setMaximumSize(QSize(16777215, 19))

        self.main_layout.addWidget(self.footer)


        self.gridLayout_2.addLayout(self.main_layout, 2, 0, 1, 1)

        QtUi.setCentralWidget(self.central_widget)

        self.retranslateUi(QtUi)

        QMetaObject.connectSlotsByName(QtUi)
    # setupUi

    def retranslateUi(self, QtUi):
        QtUi.setWindowTitle(QCoreApplication.translate("QtUi", u"Map Compositor", None))
        self.header.setText(QCoreApplication.translate("QtUi", u"MAP COMPOSITOR", None))
#if QT_CONFIG(tooltip)
        self.txt000.setToolTip(QCoreApplication.translate("QtUi", u"Set the source of maps to combine \u2014 a directory, or specific image files (use the image-files browse button).", None))
#endif // QT_CONFIG(tooltip)
        self.txt000.setPlaceholderText(QCoreApplication.translate("QtUi", u"<Source Directory or Images>", None))
#if QT_CONFIG(tooltip)
        self.txt001.setToolTip(QCoreApplication.translate("QtUi", u"Set the directory where your combined maps will be output.", None))
#endif // QT_CONFIG(tooltip)
        self.txt001.setText("")
        self.txt001.setPlaceholderText(QCoreApplication.translate("QtUi", u"<Destination Directory>", None))
#if QT_CONFIG(tooltip)
        self.txt002.setToolTip(QCoreApplication.translate("QtUi", u"Set a filename prefix for your combined maps.", None))
#endif // QT_CONFIG(tooltip)
        self.txt002.setPlaceholderText(QCoreApplication.translate("QtUi", u"<Map Name>", None))
    # retranslateUi

