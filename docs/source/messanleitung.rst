.. -*-coding: utf-8 -*-

Hinweise zur Durchführung von Messungen in Modenverwirbelungskammern
=====================================================================


Allgemeines
-----------

Alle Programmroutinen, die zur Steuerung der Geräte oder zum Erfassen
und Auswerten von Messdaten erforderlich sind, sind in der
entwickelten Software integriert. Diese wurde in der
Programmiersprache Python (http://www.python.org/) geschrieben. 

In die hinterlegten Geräteklassen
können jederzeit neue Geräte integriert werden, falls einmal der
Messaufbau erweitert werden sollte. Somit wird für die einzelnen
Messungen jeweils nur ein relativ kurzes Programm benötigt, welches
die jeweils notwendigen Routinen aufruft. Diesem Programm wird als
Parameter beim Aufruf eine kleine Konﬁgurationsdatei, die ebenfalls in
Python geschrieben wurde, übergeben. Diese Konﬁgurationsdatei wird für
jede einzelne Messung benötigt. Der Name der Kondﬁgurationsdatei
beginnt aus Übersichtsgründen mit `conf_`. In ihr sind alle für die
Messung notwendigen Parameter, wie Messbereich, Schrittweite oder die
Anzahl der zu untersuchenden Tunerpositionen enthalten, die dann
während der einzelnen Funktionsaufrufe jeweils an die Routinen
übergeben werden. 

Bei Störfestigkeitsmessungen ist es sinnvoll (wenn es mit
nicht allzu großem Aufwand realisierbar ist) eine
automatische Prüﬂingsüberwachung im Programmablauf zu integrieren. 

Es
empﬁehlt sich, für jede einzelne Messung einen seperaten Ordner
anzulegen. Dieser Ordner muss das gewünschte Messprogramm sowie die
Koﬁgurationsdatei enthalten, Weiterhin kann eine `.dot` Datei in diesem
Ordner abgelegt werden, in der der Messaufbau deﬁniert wird und auf
die noch näher eingegangen wird. Werden Messserien aufgenommen, bei
denen sich der Messaufbau nicht ändert, kann die `.dot` Datei auch
zentral abgelegt werden und der Pfad in der Konﬁgurationsdatei
entsprechend angepasst werden (mehr dazu später im Beispiel). In
diesen Ordner werden während der Messungen auch die Ergebnisse und
andere Dateien gespeichert, auf die später noch näher eingegangen
wird. 

Die übrigen Programmroutinen, Gerätetreiber und die
Initialisierungsdateien müssen nicht mit kopiert werden, da die Pfade
zu deren Speicherorten als globale Variablen hinterlegt sind. Somit
hat man abschließend für jede Messung seperate Ordner mit allen für
diese Messung relevanten Daten.

Zunächst wird ebenfalls durch das aufrufende Messprogramm eine Instanz
der Klasse :class:`MSC` erzeugt. Diese wird entweder neu oder aus bereits
vorhanden Sicherungsdateien (`pickle` files) erstellt. Die :class:`MSC` Klasse ist für die
Kommunikation mit den Messgeräten, die Messung und die Auswertung der
Messdaten zuständig. 

Dieser Instanz werden die Messparameter
`measurement_parameters` und Auswerteparameter `evaluation_parameters`
übergeben und sie führt dann die entsprechenden Befehle oder
Messroutinen durch, legt Autosavedateien an und gibt
nach erfolgter Messung die Rohdaten und nach beendeter Auswertung die
ausgewerteten Daten aus. 

Den Aufbau der Messung, also die verwendeten
Geräte und die Signalwege, erhält die Klasse durch Auswertung der
`.dot` Datei. 

Anschließend wird der gesamte Stand der abgeschlossenen
Messungen in einem `pickle` ﬁle gespeichert. Das Pickling stellt einen
sehr hilfreichen und nützlichen Algorithmus dar, mit dem sich
strukturierte Datenobjekte zu einer Bytefolge "serialisieren" und dann
in einer Datei abspeichern lassen. Diese Datei lässt sich später
wieder laden und zur ursprünglichen Datenstruktur zurückwandeln. Dies
ist nützlich, um beispielsweise an bestimmten Stellen das Messprogramm
anzuhalten und den momentanen Zustand sozusagen "einzufrieren" und
später mit weiteren Messungen fortsetzen zu können mit dem Vorteil,
dass alle vorherigen Operationen und Befehle immer noch protokolliert
und nachvollziehbar sind, da die Instanz der Klasse ja immer noch
besteht.

Der Messgraph
^^^^^^^^^^^^^^

Vor Beginn der Messungen muss der Messaufbau deﬁniert werden. Diese
Daten benötigt die Messsoftware, um die aufgenommenen Daten auswerten
zu können. Die Beschreibung des Messaufbaus erfolgt mit Hilfe eines
Graphen. In einer Datei mit der Endung `.dot` ist der Messaufbau in
Textform hinterlegt. Ein Beispiel für eine solche `.dot` Datei ist::

    digraph {
            node [fontsize=12];
            graph [fontsize=12];
            edge [fontsize=10];
            rankdir=LR;

            cbl_sg_amp [ini="M:\\umd-config\\smallMSC\\ini\\cbl_sg_amp.ini" condition="10e6 <= f <= 18e9"] [color=white, fontcolor=white ]
            cbl_amp_ant [ini="M:\\umd-config\\smallMSC\\ini\\cbl_amp_ant.ini" condition="10e6 <= f <= 4.2e9"] [color=white, fontcolor=white ]
            cbl_amp_pm1 [ini="M:\\umd-config\\smallMSC\\ini\\cbl_amp_pm1.ini" condition="10e6 <= f <= 4.2e9"] [color=white, fontcolor=white ]
            sg  [ini="M:\\umd-config\\smallMSC\\ini\\umd-gt-12000A-real.ini"] [style=filled,color=lightgrey]
            amp  [ini="M:\\umd-config\\smallMSC\\ini\\umd-ar-100s1g4-3dB-real-remote.ini" condition="800e6 <= f <= 4.2e9"] 
            ant  [ini="M:\\umd-config\\smallMSC\\ini\\umd-rs-HF906_04.ini"] [style=filled,color=lightgrey]
            refant  [ini="M:\\umd-config\\smallMSC\\ini\\umd-rs-HF906_03.ini"] [style=filled,color=lightgrey]
            tuner [ini="M:\\umd-config\\smallMSC\\ini\\umd-sms60-real.ini" ch=1] [style=filled,color=lightgrey]
            pmref [ini="M:\\umd-config\\smallMSC\\ini\\umd-rs-nrvd-2-real.ini" ch=2] [style=filled,color=lightgrey]
            pm1  [ini="M:\\umd-config\\smallMSC\\ini\\umd-rs-nrvd-1-real.ini" ch=1] [style=filled,color=lightgrey]
            pm2  [ini="M:\\umd-config\\smallMSC\\ini\\umd-rs-nrvd-1-real.ini" ch=2] [style=filled,color=lightgrey]
            cbl_ant_pm2 [ini="M:\\umd-config\\smallMSC\\ini\\cbl_ant_pm2.ini" condition="10e6 <= f <= 4.2e9"] [color=white, fontcolor=white ]
            cbl_r_pmr [ini="M:\\umd-config\\smallMSC\\ini\\cbl_r_pmr.ini" condition="10e6 <= f <= 18e9"] [color=white, fontcolor=white ]
            att20 [ini="M:\\umd-config\\smallMSC\\ini\\att20-50W.ini" condition="10e6 <= f <= 18e9"] [color=white, fontcolor=white ]
            a1 [style=filled,color=lightgrey]
            a2 [style=filled,color=lightgrey]

            subgraph cluster_amp {
                    label=amp
                    amp_in -> amp_out [dev=amp what="S21"]
            }


            sg -> a1 [dev=cbl_sg_amp what="S21"] [label="cbl_sg_amp"]
            a1 -> amp_in
            amp_out -> a2
            a2 -> ant [dev=cbl_amp_ant what="S21"]  [label="cbl_amp_ant"]
            a2 -> pm1 [dev=cbl_amp_pm1 what="S21"]  [label="cbl_amp_pm1"]
            refant -> feedthru [dev=cbl_r_pmr what="S21"]  [label="cbl_r_pmr"]
            feedthru -> pmref [dev=att20 what="S21"]  [label="att20"]
            ant -> pm2 [dev=cbl_ant_pm2 what="S21"]  [label="cbl_ant_pm2"]

            subgraph "cluster_msc" {label=MSC; ant; refant}

            subgraph "cluster_pmoutput" {label="output"; pm1; pm2; pmref;}
            }


.. graphviz::

   digraph {
            node [fontsize=12];
            graph [fontsize=12];
            edge [fontsize=10];
            rankdir=LR;

            cbl_sg_amp [ini="M:\\umd-config\\smallMSC\\ini\\cbl_sg_amp.ini" condition="10e6 <= f <= 18e9"] [color=white, fontcolor=white ]
            cbl_amp_ant [ini="M:\\umd-config\\smallMSC\\ini\\cbl_amp_ant.ini" condition="10e6 <= f <= 4.2e9"] [color=white, fontcolor=white ]
            cbl_amp_pm1 [ini="M:\\umd-config\\smallMSC\\ini\\cbl_amp_pm1.ini" condition="10e6 <= f <= 4.2e9"] [color=white, fontcolor=white ]
            sg  [ini="M:\\umd-config\\smallMSC\\ini\\umd-gt-12000A-real.ini"] [style=filled,color=lightgrey]
            amp  [ini="M:\\umd-config\\smallMSC\\ini\\umd-ar-100s1g4-3dB-real-remote.ini" condition="800e6 <= f <= 4.2e9"] 
            ant  [ini="M:\\umd-config\\smallMSC\\ini\\umd-rs-HF906_04.ini"] [style=filled,color=lightgrey]
            refant  [ini="M:\\umd-config\\smallMSC\\ini\\umd-rs-HF906_03.ini"] [style=filled,color=lightgrey]
            tuner [ini="M:\\umd-config\\smallMSC\\ini\\umd-sms60-real.ini" ch=1] [style=filled,color=lightgrey]
            pmref [ini="M:\\umd-config\\smallMSC\\ini\\umd-rs-nrvd-2-real.ini" ch=2] [style=filled,color=lightgrey]
            pm1  [ini="M:\\umd-config\\smallMSC\\ini\\umd-rs-nrvd-1-real.ini" ch=1] [style=filled,color=lightgrey]
            pm2  [ini="M:\\umd-config\\smallMSC\\ini\\umd-rs-nrvd-1-real.ini" ch=2] [style=filled,color=lightgrey]
            cbl_ant_pm2 [ini="M:\\umd-config\\smallMSC\\ini\\cbl_ant_pm2.ini" condition="10e6 <= f <= 4.2e9"] [color=white, fontcolor=white ]
            cbl_r_pmr [ini="M:\\umd-config\\smallMSC\\ini\\cbl_r_pmr.ini" condition="10e6 <= f <= 18e9"] [color=white, fontcolor=white ]
            att20 [ini="M:\\umd-config\\smallMSC\\ini\\att20-50W.ini" condition="10e6 <= f <= 18e9"] [color=white, fontcolor=white ]
            a1 [style=filled,color=lightgrey]
            a2 [style=filled,color=lightgrey]

            subgraph cluster_amp {
                    label=amp
                    amp_in -> amp_out [dev=amp what="S21"]
            }


            sg -> a1 [dev=cbl_sg_amp what="S21"] [label="cbl_sg_amp"]
            a1 -> amp_in
            amp_out -> a2
            a2 -> ant [dev=cbl_amp_ant what="S21"]  [label="cbl_amp_ant"]
            a2 -> pm1 [dev=cbl_amp_pm1 what="S21"]  [label="cbl_amp_pm1"]
            refant -> feedthru [dev=cbl_r_pmr what="S21"]  [label="cbl_r_pmr"]
            feedthru -> pmref [dev=att20 what="S21"]  [label="att20"]
            ant -> pm2 [dev=cbl_ant_pm2 what="S21"]  [label="cbl_ant_pm2"]

            subgraph "cluster_msc" {label=MSC; ant; refant}

            subgraph "cluster_pmoutput" {label="output"; pm1; pm2; pmref;}
            }



Als Beschreibungssprache für den Graphen wird DOT-language
benutzt. Weitere Informationen zu dieser Spache sind unter
http://www.graphviz.org/ zu ﬁnden.

Nach einigen globalen (optionalen) Anweisungen zur Graphenvisualisierung werden
zunächst alle verwendeten Geräte und Kabel aufgelistet und somit als
Knoten im Graphen deﬁniert. 

In unserem Beispielfall ﬁnden also ein
Signalgenerator (`sg`), diverse Kabel (`cbl`), ein Abschwächer (`att`), ein
Verstärker (`amp`), eine Sende- und eine Referenzantenne (`ant`), der
Rührer (`tuner`) und einige Leistungsmesser (`pm`) Anwendung. 

Die Kabel
und der Abschwächer, die eigentlich als Verbindungen, also als Kanten
im Graphen fungieren, wurden hier ebenfalls als Knoten deklariert, da
dies die spätere Parameterübergabe an das Messprogramm erleichtert. 

In
den ersten eckigen Klammern hinter den Geräten werden diese für die
Messung relevanten Parameter der entsprechenden Geräte übergeben. Als
Parameter wird auf jeden Fall der Dateiname der Initialisierungsdatei des Geräts benötigt. 
Dies ist eine
Textdatei mit der Endung `.ini`, in der alle wichtigen Informationen
über das entsprechende Gerät hinterlegt sind. 

Weitere mögliche
Parameter sind zum Beispiel der Arbeitsbereich der Geräte, die als
`condition` deﬁniert werden. Weiterhin ist es möglich, beim Erreichen
dieser `condition` bestimmte Aktionen, die als `action` deﬁniert werden,
auszuführen. 

In den zweiten eckigen Klammern sind Attribute zur
Visualisierung des Graphen zu ﬁnden. 

Anschließend beginnt die
eigentliche Beschreibung des Messaufbaus. Hierbei wird deﬁniert, wie
und in welche Richtungen die einzelnen Geräte (Knoten) miteinander
verbunden sind. Abbildung 1.1 stellt den im `.dot` ﬁle beschriebenen
Aufbau noch einmal graﬁsch dar. Zur Visualisierung des `.dot` ﬁles wurde
das Programm :program:`Graphviz` benutzt, das sich ebenfalls auf
der oben angegebenen Homepage herunterladen lässt. 

Bei der Darstellung wurden allerdings aus Gründen der Übersichtlichkeit alle Knoten, die die 
Verbindungen repräsentieren, also keine wirklichen Knoten sind, ausgeblendet.

Bei jeder Art von Messungen gibt es bestimmte Knoten, die auf alle Fälle im Messaufbau enthalten sein müssen. 
Diese sind hier grau markiert. Dieser Aufbau ﬁndet bei Störemissions- und Störfestigkeitsmessungen Anwendung. 
Als weiteres Beispiel sei noch ein typischer Aufbau für die Kalibrierung einer Modenverwirbelungskammer angefügt::

   digraph {
            node [fontsize=12];
            graph [fontsize=12];
            edge [fontsize=10];
            rankdir=LR;


            sg  [ ini="M:\\umd-config\\largeMSC\\ini\\umd-rs-smr-real.ini"  ] [style=filled,color=lightgrey]
            fp1 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-1-real.ini"] [style=filled,color=lightgrey]
            fp2 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-2-real.ini"] [style=filled,color=lightgrey]
            fp3 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-3-real.ini"] [style=filled,color=lightgrey]
            fp4 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-4-real.ini"] [style=filled,color=lightgrey]
            fp5 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-5-real.ini"] [style=filled,color=lightgrey]
            fp6 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-6-real.ini"] [style=filled,color=lightgrey]
            fp7 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-7-real.ini"] [style=filled,color=lightgrey]
            fp8 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-8-real.ini"] [style=filled,color=lightgrey]
            tuner1 [ini="M:\\umd-config\\largeMSC\\ini\\umd-mc-hd-100-real.ini" ch=2] [style=filled,color=lightgrey]
            ant1  [ini="M:\\umd-config\\largeMSC\\ini\\umd-sb-VULP9118-C_513.ini" condition="f <= 1e9" ]
            ant2  [ini="M:\\umd-config\\largeMSC\\ini\\umd-rs-HF906_04.ini" condition="f > 1e9" ]
            refant [style=filled,color=lightgrey]
            refant1  [ini="M:\\umd-config\\largeMSC\\ini\\umd-sb-VULP9118-C_514.ini" condition="f <= 1e9" ]
            refant2  [ini="M:\\umd-config\\largeMSC\\ini\\umd-rs-HF906_03.ini" condition="f > 1e9" ]
            pmref1  [ini="M:\\umd-config\\largeMSC\\ini\\umd-rs-nrvs-real.ini" ch=1] [style=filled,color=lightgrey]
            pm2  [ini="M:\\umd-config\\largeMSC\\ini\\umd-rs-nrvd-real.ini" ch=2] [style=filled,color=lightgrey]
            pm1  [ini="M:\\umd-config\\largeMSC\\ini\\umd-rs-nrvd-real.ini" ch=1] [style=filled,color=lightgrey]
            sw [ini="M:\\umd-config\\largeMSC\\ini\\umd-umd-sb-real.ini" ch=1]
            sta [ini="M:\\umd-config\\largeMSC\\ini\\umd-umd-sb-real.ini" ch=2]
            amp1  [ini="M:\\umd-config\\largeMSC\\ini\\amplifier1.ini" condition="f <= 1e9" action="import custom\ncustom.my_switch(self.sw, 'f', 1e9)"]
            amp2  [ini="M:\\umd-config\\largeMSC\\ini\\amplifier2.ini" condition="f > 1e9"  action="import custom\ncustom.my_switch(self.sw, 'f', 1e9)"]
            a1 [style=filled,color=lightgrey]
            a2 [style=filled,color=lightgrey]
            ant [style=filled,color=lightgrey]
            cbl_r1_pmr [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-PM-Ref-Ant_LF-10db.ini" condition="f <= 360e6" action="import custom\ncustom.my_switch(self.sta, 'f', 360e6)"] [color=white, fontcolor=white ]
            cbl_r2_pmr [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-PM-Ref-Ant_LF-0db.ini" condition="360e6 < f <= 1e9"action="import custom\ncustom.my_switch(self.sta, 'f', 360e6)"] [color=white, fontcolor=white ]
            cbl_r3_pmr [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-PM-Ref-Ant_HF-0db.ini" condition="f > 1e9"] [color=white, fontcolor=white ]
            cbl_sg_amp1 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-SG-AMP_LF.ini" condition="f <= 1e9"] [color=white, fontcolor=white ]
            cbl_sg_amp2 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-SG-AMP_HF.ini" condition="f > 1e9"] [color=white, fontcolor=white ]
            cbl_amp1_ant1 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-AMP-ANT_LF.ini" condition="f <= 1e9"] [color=white, fontcolor=white ]
            cbl_amp2_ant2 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-AMP-ANT_HF.ini" condition="f > 1e9"] [color=white, fontcolor=white ]
            cbl_amp1_pm1 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-PM-FWD_LF.ini" condition="f <= 1e9"] [color=white, fontcolor=white ]
            cbl_amp2_pm1 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-PM-FWD_HF.ini" condition="f > 1e9"] [color=white, fontcolor=white ]
            cbl_ant1_pm2 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-PM-REV_LF.ini" condition="f <= 1e9"] [color=white, fontcolor=white ]
            cbl_ant2_pm2 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-PM-REV_HF.ini" condition="f > 1e9"] [color=white, fontcolor=white ]



            subgraph cluster_amp1 {
                label=amp1
                a1_a1 -> a2_e1 [dev=amp1 what="S21"]
            }
            subgraph cluster_amp2 {
                label=amp2
                a1_a2 -> a2_e2 [dev=amp2 what="S21"]
            }

            subgraph cluster_pm_in {label=pm_in; pm1_e1; pm1_e2; pm2_e1; pm2_e2; pmref1_e1; pmref1_e2; pmref1_e3}


            subgraph cluster_msc {label=MSC; tuner1; ant; ant_a1; ant_a2; ant_e1; ant_e2; ant1; ant2; refant; refant1; refant2; refant_a1; refant_a2; refant_a3}


            subgraph cluster_pmoutput {label=output; pm1; pm2 ;pmref1;}


            sg -> sg_a1
            sg -> sg_a2
            sg_a1 -> a1_e1 [dev=cbl_sg_amp1 what="S21"] [label=cbl_sg_amp1]
            sg_a2 -> a1_e2 [dev=cbl_sg_amp2 what="S21"] [label=cbl_sg_amp2]
            a1_e1 -> a1
            a1_e2 -> a1
            a1 -> a1_a1
            a1 -> a1_a2
            a2_e1 -> a2
            a2_e2 -> a2
            a2 -> a2_a1
            a2 -> a2_a2
            a2_a1 -> ant_e1 [dev=cbl_amp1_ant1 what="S21"] [label=cbl_amp1_ant1]
            a2_a2 -> ant_e2 [dev=cbl_amp2_ant2 what="S21"] [label=cbl_amp2_ant2]
            ant_e1 -> ant
            ant_e2 -> ant
            ant -> ant1 
            ant1 -> ant 
            ant -> ant2 
            ant2 -> ant 
            ant -> ant_a1
            ant -> ant_a2
            a2_a1 -> pm1_e1 [dev=cbl_amp1_pm1 what="S21"] [label=cbl_amp1_pm1]
            a2_a2 -> pm1_e2 [dev=cbl_amp2_pm1 what="S21"] [label=cbl_amp2_pm1]
            pm1_e1 -> pm1
            pm1_e2 -> pm1
            ant_a1 -> pm2_e1 [dev=cbl_ant1_pm2 what="S21"] [label=cbl_ant1_pm2]
            ant_a2 -> pm2_e2 [dev=cbl_ant2_pm2 what="S21"] [label=cbl_ant2_pm2]
            pm2_e1 -> pm2
            pm2_e2 -> pm2
            refant1 -> refant
            refant2 -> refant
            refant -> refant_a1
            refant -> refant_a2
            refant -> refant_a3
            refant_a3 -> pmref1_e3  [dev=cbl_r3_pmr what="S21"] [label=cbl_r3_pmr]
            refant_a2 -> pmref1_e2  [dev=cbl_r2_pmr what="S21"] [label=cbl_r2_pmr]
            refant_a1 -> pmref1_e1 [dev=cbl_r1_pmr what="S21"] [label=cbl_r1_pmr]
            pmref1_e1 -> pmref1
            pmref1_e2 -> pmref1
            pmref1_e3 -> pmref1	
           }

.. _dot-kalibrieraufbau:

.. graphviz::

   digraph {
            node [fontsize=12];
            graph [fontsize=12];
            edge [fontsize=10];
            rankdir=LR;


            sg  [ ini="M:\\umd-config\\largeMSC\\ini\\umd-rs-smr-real.ini"  ] [style=filled,color=lightgrey]
            fp1 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-1-real.ini"] [style=filled,color=lightgrey]
            fp2 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-2-real.ini"] [style=filled,color=lightgrey]
            fp3 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-3-real.ini"] [style=filled,color=lightgrey]
            fp4 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-4-real.ini"] [style=filled,color=lightgrey]
            fp5 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-5-real.ini"] [style=filled,color=lightgrey]
            fp6 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-6-real.ini"] [style=filled,color=lightgrey]
            fp7 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-7-real.ini"] [style=filled,color=lightgrey]
            fp8 [ini="M:\\umd-config\\largeMSC\\ini\\umd-narda-emc300-8-real.ini"] [style=filled,color=lightgrey]
            tuner1 [ini="M:\\umd-config\\largeMSC\\ini\\umd-mc-hd-100-real.ini" ch=2] [style=filled,color=lightgrey]
            ant1  [ini="M:\\umd-config\\largeMSC\\ini\\umd-sb-VULP9118-C_513.ini" condition="f <= 1e9" ]
            ant2  [ini="M:\\umd-config\\largeMSC\\ini\\umd-rs-HF906_04.ini" condition="f > 1e9" ]
            refant [style=filled,color=lightgrey]
            refant1  [ini="M:\\umd-config\\largeMSC\\ini\\umd-sb-VULP9118-C_514.ini" condition="f <= 1e9" ]
            refant2  [ini="M:\\umd-config\\largeMSC\\ini\\umd-rs-HF906_03.ini" condition="f > 1e9" ]
            pmref1  [ini="M:\\umd-config\\largeMSC\\ini\\umd-rs-nrvs-real.ini" ch=1] [style=filled,color=lightgrey]
            pm2  [ini="M:\\umd-config\\largeMSC\\ini\\umd-rs-nrvd-real.ini" ch=2] [style=filled,color=lightgrey]
            pm1  [ini="M:\\umd-config\\largeMSC\\ini\\umd-rs-nrvd-real.ini" ch=1] [style=filled,color=lightgrey]
            sw [ini="M:\\umd-config\\largeMSC\\ini\\umd-umd-sb-real.ini" ch=1]
            sta [ini="M:\\umd-config\\largeMSC\\ini\\umd-umd-sb-real.ini" ch=2]
            amp1  [ini="M:\\umd-config\\largeMSC\\ini\\amplifier1.ini" condition="f <= 1e9" action="import custom\ncustom.my_switch(self.sw, 'f', 1e9)"]
            amp2  [ini="M:\\umd-config\\largeMSC\\ini\\amplifier2.ini" condition="f > 1e9"  action="import custom\ncustom.my_switch(self.sw, 'f', 1e9)"]
            a1 [style=filled,color=lightgrey]
            a2 [style=filled,color=lightgrey]
            ant [style=filled,color=lightgrey]
            cbl_r1_pmr [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-PM-Ref-Ant_LF-10db.ini" condition="f <= 360e6" action="import custom\ncustom.my_switch(self.sta, 'f', 360e6)"] [color=white, fontcolor=white ]
            cbl_r2_pmr [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-PM-Ref-Ant_LF-0db.ini" condition="360e6 < f <= 1e9"action="import custom\ncustom.my_switch(self.sta, 'f', 360e6)"] [color=white, fontcolor=white ]
            cbl_r3_pmr [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-PM-Ref-Ant_HF-0db.ini" condition="f > 1e9"] [color=white, fontcolor=white ]
            cbl_sg_amp1 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-SG-AMP_LF.ini" condition="f <= 1e9"] [color=white, fontcolor=white ]
            cbl_sg_amp2 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-SG-AMP_HF.ini" condition="f > 1e9"] [color=white, fontcolor=white ]
            cbl_amp1_ant1 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-AMP-ANT_LF.ini" condition="f <= 1e9"] [color=white, fontcolor=white ]
            cbl_amp2_ant2 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-AMP-ANT_HF.ini" condition="f > 1e9"] [color=white, fontcolor=white ]
            cbl_amp1_pm1 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-PM-FWD_LF.ini" condition="f <= 1e9"] [color=white, fontcolor=white ]
            cbl_amp2_pm1 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-PM-FWD_HF.ini" condition="f > 1e9"] [color=white, fontcolor=white ]
            cbl_ant1_pm2 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-PM-REV_LF.ini" condition="f <= 1e9"] [color=white, fontcolor=white ]
            cbl_ant2_pm2 [ini="M:\\umd-config\\largeMSC\\ini\\umd-cable-PM-REV_HF.ini" condition="f > 1e9"] [color=white, fontcolor=white ]



            subgraph cluster_amp1 {
                label=amp1
                a1_a1 -> a2_e1 [dev=amp1 what="S21"]
            }
            subgraph cluster_amp2 {
                label=amp2
                a1_a2 -> a2_e2 [dev=amp2 what="S21"]
            }

            subgraph cluster_pm_in {label=pm_in; pm1_e1; pm1_e2; pm2_e1; pm2_e2; pmref1_e1; pmref1_e2; pmref1_e3}


            subgraph cluster_msc {label=MSC; tuner1; ant; ant_a1; ant_a2; ant_e1; ant_e2; ant1; ant2; refant; refant1; refant2; refant_a1; refant_a2; refant_a3}


            subgraph cluster_pmoutput {label=output; pm1; pm2 ;pmref1;}


            sg -> sg_a1
            sg -> sg_a2
            sg_a1 -> a1_e1 [dev=cbl_sg_amp1 what="S21"] [label=cbl_sg_amp1]
            sg_a2 -> a1_e2 [dev=cbl_sg_amp2 what="S21"] [label=cbl_sg_amp2]
            a1_e1 -> a1
            a1_e2 -> a1
            a1 -> a1_a1
            a1 -> a1_a2
            a2_e1 -> a2
            a2_e2 -> a2
            a2 -> a2_a1
            a2 -> a2_a2
            a2_a1 -> ant_e1 [dev=cbl_amp1_ant1 what="S21"] [label=cbl_amp1_ant1]
            a2_a2 -> ant_e2 [dev=cbl_amp2_ant2 what="S21"] [label=cbl_amp2_ant2]
            ant_e1 -> ant
            ant_e2 -> ant
            ant -> ant1 
            ant1 -> ant 
            ant -> ant2 
            ant2 -> ant 
            ant -> ant_a1
            ant -> ant_a2
            a2_a1 -> pm1_e1 [dev=cbl_amp1_pm1 what="S21"] [label=cbl_amp1_pm1]
            a2_a2 -> pm1_e2 [dev=cbl_amp2_pm1 what="S21"] [label=cbl_amp2_pm1]
            pm1_e1 -> pm1
            pm1_e2 -> pm1
            ant_a1 -> pm2_e1 [dev=cbl_ant1_pm2 what="S21"] [label=cbl_ant1_pm2]
            ant_a2 -> pm2_e2 [dev=cbl_ant2_pm2 what="S21"] [label=cbl_ant2_pm2]
            pm2_e1 -> pm2
            pm2_e2 -> pm2
            refant1 -> refant
            refant2 -> refant
            refant -> refant_a1
            refant -> refant_a2
            refant -> refant_a3
            refant_a3 -> pmref1_e3  [dev=cbl_r3_pmr what="S21"] [label=cbl_r3_pmr]
            refant_a2 -> pmref1_e2  [dev=cbl_r2_pmr what="S21"] [label=cbl_r2_pmr]
            refant_a1 -> pmref1_e1 [dev=cbl_r1_pmr what="S21"] [label=cbl_r1_pmr]
            pmref1_e1 -> pmref1
            pmref1_e2 -> pmref1
            pmref1_e3 -> pmref1	
           }
   

In Abbildung :ref:`dot-kalibrieraufbau` ist der entsprechende Aufbau zu sehen. 

Hier sind zusätzlich noch die für die Kalibrierung notwendigen 8
Feldsonden zu sehen. Weiterhin werden in dieser MVK auf Grund
ihres Arbeitsbereiches je nach Frequenzbereich unterschiedliche
Antennen und Verstärker benutzt, zwischen denen entsprechend im
Programmablauf hin- und hergeschaltet wird. 

Auch hier markieren die
grauen Knoten wieder die bei einer Kalibrierung unbedingt
erforderlichen Knoten. Hier ist bei den Verstärkern und Kabeln zu
sehen, dass beim Erreichen von 360 MHz bzw. 1 GHz, dies ist als
*condition* festgelegt, eine *action* auszuführen ist. Dies ist in diesem
Fall das Umschalten des Signalpfades. Zum einen wird bei Frequenzen
unterhalb von 360 MHz ein Abschwächer im Signalpfad benutzt, der dann
auf einem anderen Signalpfad umgangen wird. Zum anderen werden bei
Messungen oberhalb von 1 GHz andere Antennen und Verstärker benutzt,
so dass auch beim Erreichen dieser Frequenz der Signalpfad geändert
werden muss. Das Umschalten der Pfade wird programmgesteuert über die
Umschalter *sta* und *sw* realisiert.

Die Initialisierungsdatei
^^^^^^^^^^^^^^^^^^^^^^^^^^

Wie bereits erwähnt, ist die `.ini` Datei die Datei, in der alle
Startattribute für die einzelnen Geräte festgelegt sind. Wenn dem
aufrufenden Messprogramm keine anderen Attribute übergeben werden,
werden die Geräte mit den in der .ini-Datei festgelegten Parametern
initialisiert. Im nächsten Listing ist als Beispiel die
Initialisierungsdatei für den Signalgenerator `SMT06` der Firma R&S zu
sehen. Anhand dieser noch recht übersichtlichen Datei soll kurz auf
deren Aufbau eingegangen werden::

   [description]
   DESCRIPTION = "Rohde&Schwarz SMT20 Signal Generator"
   TYPE = "SIGNALGENERATOR"
   VENDOR ="Rohde&Schwarz"
   SERIALNR = ""
   DEVICEID = ""
   DRIVER = "M:\\dlls\\umd-rs-smt.dll"
   NR_OF_CHANNELS = "1"

   [INIT_VALUE]
   FSTART = "5e3"
   FSTOP = "6e9"
   FSTEP = "1.0"
   GPIB = "28"
   VIRTUAL = "1"

   [CHANNEL_1]
   NAME = "RF Out"
   LEVEL = "-100"
   UNIT = "dBm"
   LEVELOFFSET = "0.0"
   LEVELLIMIT = "0.0"
   OUTPUTSTATE = "0"
   LFOUTPUTSTATE = "0"
   ATTMODE = "0"
   OPERATINGMODE = "0"

Die `.ini` Datei enthält eine Reihe von für diese Gerätefamilie
nötigen Keys mit entsprechenden Werten. 

Die ersten Blöcke sind für
alle Geräte gleich. Im ersten, allgemeinen, Block wird der Name, Typ
und Hersteller festgehalten. Falls bekannt, kann in diesem Block auch
die Seriennummer und ID des Gerätes festgehalten werden. Letzlich wird
der Speicherort des Treibers für das Gerät und die Anzahl der
möglichen Kanäle des Gerätes übergeben. Im zweiten Block werden Start-
und Stopfrequenz, die Schrittweite, die GPIB-Adresse und die
Betriebsart übergeben. Zum Schluss folgt für jeden nutzbaren Kanal des
Gerätes ein Block, in dem die für dieses Gerät typischen
Einstellmöglichkeiten mit Startwerten belegt werden, damit beim
Initialisieren der Geräte keine undeﬁnierten Zustände entstehen oder
Einstellungen von alten Messungen beibehalten werden, die evtl. den
aktuellen Messaufbau zum Beispiel durch zu hohe Feldstärken gefährden.


Kalibriermessungen
-------------------

Der Ablauf einer typischen Kalibriermessung soll am Beispiel der Kalibrierung einer leeren Modenverwirbelungskammer erläutert werden. Wie bereits angesprochen, ist es günstiger, für jede Messung einen gesonderten Ordner zu benutzen, um in diesem alle Daten zu speichern. In dieses Ordner gehören jeweils die Konﬁgurationsdatei, das aufrufende Messprogramm und evtl. die entsprechende .dot-Datei. In der fogenden Abbildung  ist ein Beispiel für den Inhalt eines Messordners zu sehen. Zusätzlich beﬁndet sich im Ordner noch eine zweite Konﬁgurationsdatei für die Auswertung und zwei Batchdateien, mit denen die Messung oder Auswertung auch gestartet werden kann.

.. figure:: messordner-before.png

   Messordnerinhalt vor Beginn der Messungen


Vorbereitungen
^^^^^^^^^^^^^^^

Die dot-Datei
"""""""""""""

Die `.dot` Datei wurde in diesem Fall im globalen Verzeichnis der `.dot` Dateien hinterlegt. 

Sie ist im folgendem Listing dargestellt::

   digraph {node [fontsize=12];
            graph [fontsize=12]; 
            edge [fontsize=10]; 
            rankdir=LR;

            sg [ini="C:\\UMD\\umd−config\\ini\\rs−smg.ini"] [style=filled, color=lightgrey]
	    fp1 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−1.ini"ch=1] [style=filled,color=lightgrey]
	    fp2 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−1.ini"ch=2] [style=filled,color=lightgrey]
	    fp3 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−1.ini"ch=3] [style=filled,color=lightgrey]
	    fp4 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−1.ini"ch=4] [style=filled,color=lightgrey]
	    fp5 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−2.ini"ch=1] [style=filled,color=lightgrey]
	    fp6 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−2.ini"ch=2] [style=filled,color=lightgrey]
	    fp7 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−2.ini"ch=3] [style=filled,color=lightgrey]
	    fp8 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−2.ini"ch=4] [style=filled,color=lightgrey]
	    amp [ini="C:\\UMD\\umd−config\\ini\\AR80W1000M1.ini"]
	    tuner [ini="C:\\UMD\\umd−config\\ini\\tuner.ini"] [style=filled,color=lightgrey]
	    ant [ini="C:\\UMD\\umd−config\\ini\\AT4000A.ini" condition="200e6<f<=1e9"] [style=filled,color=lightgrey]
	    refant [ini="C:\\UMD\\umd−config\\ini\\HL223.ini" condition="200e6<f<=1.3e9"] [style=filled,color=lightgrey]
	    pmref [ini="C:\\UMD\\umd−config\\ini\\NRV−Rx.ini"ch=1] [style=filled,color=lightgrey]
	    pm1 [ini="C:\\UMD\\umd−config\\ini\\NRVPA.ini"ch=1] [style=filled,color=lightgrey]
	    pm2 [ini="C:\\UMD\\umd−config\\ini\\NRVPA.ini"ch=2] [style=filled,color=lightgrey]

	    a1 [style=filled,color=lightgrey]
 	    a2 [style=filled,color=lightgrey]
	    conn_sg_amp [ini="C:\\UMD\\umd−config\\ini\\CONNSMG−−PA4.ini" condition="80e6<=f<=1e9"] [color=white,fontcolor=white]
	    conn_amp_msc [ini="C:\\UMD\\umd−config\\ini\\CONN−PA4−MSC.ini" condition="80e6<=f<=1e9"] [color=white,fontcolor=white]
	    conn_msc_ant [ini="C:\\UMD\\umd−config\\ini\\CBL−716G3.ini" condition="80e6<=f<=1e9"] [color=white,fontcolor=white]
	    conn_amp_dc_fwd [ini="C:\\UMD\\umd−config\\ini\\CONN−Bonn_BDC0810_Fwd_7−16.ini" condition="80e6<=f<=1e9"] [color=white,fontcolor=white]
	    conn_msc_dc_rev [ini="C:\\UMD\\umd−config\\ini\\CONN−Bonn_BDC0810_Rev_7−16.ini" condition="80e6<=f<=1e9"] [color=white,fontcolor=white]
	    conn_dc_fwd_pm1 [ini="C:\\UMD\\umd−config\\ini\\CONN−PA4−NRV_A.ini" condition="80e6<=f<=1e9"] [color=white,fontcolor=white]
	    conn_dc_rev_pm2 [ini="C:\\UMD\\umd−config\\ini\\CONN−PA4−NRV_B.ini" condition="80e6<=f<=1e9"] [color=white,fontcolor=white]
	    conn_refant_att [ini="C:\\UMD\\umd−config\\ini\\CONN−HL223−NRV_RX_Antenna.ini" condition="80e6<=f<=1e9"] [color=white, fontcolor=white]
	    conn_att_pmref [ini="C:\\UMD\\umd−config\\ini\\CONN−Weinschel−46−20−34.ini" condition="f<=18e9"] [color=white,fontcolor=white]
	    cbl_rg214_5m_2003 [ini="C:\\UMD\\umd−config\\ini\\CBL−RG214−5m−2003.ini" condition="80e6<=f<=1e9"] [color=white, fontcolor=white]


	    subgraph cluster_amp {
	    	     label=amp
	    	     amp_in -> amp [dev=amp what="S21"]
		     amp -> amp_out}

	    subgraph cluster_pm_in {
	    	     label=pm_in;
		     pm1_e1;
		     pm2_e1;
		     pmref_e1}

	    subgraph cluster_feedthrough {
	    	     label=feedthrough;
		     msc_in;
		     msc_out}

	    subgraph cluster_msc {
	    	     label=MSC;
		     tuner;
		     fp1;
		     fp2;
		     fp3;
		     fp4;
		     fp5;
		     fp6;
		     fp7;
		     fp8;
		     ant;
		     refant;
		     refant_a1}

	    subgraph cluster_dc {
	    	     label=dc;
		     dc_fwd;
		     dc_rev}

	    subgraph cluster_pmoutput {
	    	     label=pmoutput;
		     pm1;
		     pm2;
		     pmref}

	    subgraph cluster_e_fieldoutput {
	    	     label=e_fieldoutput;
		     field_mon1;
		     field_mon2}

	    sg -> a1 [dev=conn_sg_amp what="S21"] [label=conn_sg_amp]
	    a1 -> amp_in
	    amp_out -> a2
	    a2 -> a21 [dev=cbl_rg214_5m_2003 what="S21"] [label=cbl_rg214_5m_2003]
	    a21 -> msc_in [dev=conn_amp_msc what="S21"] [label=conn_amp_msc]
	    msc_in -> ant [dev=conn_msc_ant what="S21"] [label=cbl_msc_ant]
	    ant -> msc_out [dev=conn_msc_ant what="S21"] [label=cbl_msc_ant]
	    a2 -> dc_fwd [dev=conn_amp_dc_fwd what="S21"] [label=conn_amp_dc_fwd]
	    dc_fwd -> pm1_e1 [dev=conn_dc_fwd_pm1 what="S21"] [label=conn_dc_fwd_pm1]
	    pm1_e1 -> pm1
	    msc_out -> dc_rev [dev=conn_msc_dc_rev what="S21"] [label=conn_msc_dc_rev]
	    dc_rev -> pm2_e1 [dev=conn_dc_rev_pm2 what="S21"] [label=conn_dc_rev_pm2]
	    pm2_e1 -> pm2
	    refant -> refant_a1
	    refant_a1 -> att [dev=conn_refant_att what="S21"] [label=conn_refant_att]
	    att -> pmref_e1 [dev=conn_att_pmref what="S21"] [label=conn_att_pmref]
	    pmref_e1 -> pmref
	    fp1 -> field_mon1
	    fp2 -> field_mon1
	    fp3 -> field_mon1
	    fp4 -> field_mon1
	    fp5 -> field_mon2
	    fp6 -> field_mon2
	    fp7 -> field_mon2
	    fp8 -> field_mon2}


Der entsprechende Messgraph sieht wie folgt aus:

.. graphviz::

   digraph {node [fontsize=12];
            graph [fontsize=12]; 
            edge [fontsize=10]; 
            rankdir=LR;

            sg [ini="C:\\UMD\\umd−config\\ini\\rs−smg.ini"] [style=filled, color=lightgrey]
	    fp1 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−1.ini"ch=1] [style=filled,color=lightgrey]
	    fp2 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−1.ini"ch=2] [style=filled,color=lightgrey]
	    fp3 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−1.ini"ch=3] [style=filled,color=lightgrey]
	    fp4 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−1.ini"ch=4] [style=filled,color=lightgrey]
	    fp5 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−2.ini"ch=1] [style=filled,color=lightgrey]
	    fp6 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−2.ini"ch=2] [style=filled,color=lightgrey]
	    fp7 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−2.ini"ch=3] [style=filled,color=lightgrey]
	    fp8 [ini="C:\\UMD\\umd−config\\ini\\ar−fm7004−2.ini"ch=4] [style=filled,color=lightgrey]
	    amp [ini="C:\\UMD\\umd−config\\ini\\AR80W1000M1.ini"]
	    tuner [ini="C:\\UMD\\umd−config\\ini\\tuner.ini"] [style=filled,color=lightgrey]
	    ant [ini="C:\\UMD\\umd−config\\ini\\AT4000A.ini" condition="200e6<f<=1e9"] [style=filled,color=lightgrey]
	    refant [ini="C:\\UMD\\umd−config\\ini\\HL223.ini" condition="200e6<f<=1.3e9"] [style=filled,color=lightgrey]
	    pmref [ini="C:\\UMD\\umd−config\\ini\\NRV−Rx.ini"ch=1] [style=filled,color=lightgrey]
	    pm1 [ini="C:\\UMD\\umd−config\\ini\\NRVPA.ini"ch=1] [style=filled,color=lightgrey]
	    pm2 [ini="C:\\UMD\\umd−config\\ini\\NRVPA.ini"ch=2] [style=filled,color=lightgrey]

	    a1 [style=filled,color=lightgrey]
 	    a2 [style=filled,color=lightgrey]
	    conn_sg_amp [ini="C:\\UMD\\umd−config\\ini\\CONNSMG−−PA4.ini" condition="80e6<=f<=1e9"] [color=white,fontcolor=white]
	    conn_amp_msc [ini="C:\\UMD\\umd−config\\ini\\CONN−PA4−MSC.ini" condition="80e6<=f<=1e9"] [color=white,fontcolor=white]
	    conn_msc_ant [ini="C:\\UMD\\umd−config\\ini\\CBL−716G3.ini" condition="80e6<=f<=1e9"] [color=white,fontcolor=white]
	    conn_amp_dc_fwd [ini="C:\\UMD\\umd−config\\ini\\CONN−Bonn_BDC0810_Fwd_7−16.ini" condition="80e6<=f<=1e9"] [color=white,fontcolor=white]
	    conn_msc_dc_rev [ini="C:\\UMD\\umd−config\\ini\\CONN−Bonn_BDC0810_Rev_7−16.ini" condition="80e6<=f<=1e9"] [color=white,fontcolor=white]
	    conn_dc_fwd_pm1 [ini="C:\\UMD\\umd−config\\ini\\CONN−PA4−NRV_A.ini" condition="80e6<=f<=1e9"] [color=white,fontcolor=white]
	    conn_dc_rev_pm2 [ini="C:\\UMD\\umd−config\\ini\\CONN−PA4−NRV_B.ini" condition="80e6<=f<=1e9"] [color=white,fontcolor=white]
	    conn_refant_att [ini="C:\\UMD\\umd−config\\ini\\CONN−HL223−NRV_RX_Antenna.ini" condition="80e6<=f<=1e9"] [color=white, fontcolor=white]
	    conn_att_pmref [ini="C:\\UMD\\umd−config\\ini\\CONN−Weinschel−46−20−34.ini" condition="f<=18e9"] [color=white,fontcolor=white]
	    cbl_rg214_5m_2003 [ini="C:\\UMD\\umd−config\\ini\\CBL−RG214−5m−2003.ini" condition="80e6<=f<=1e9"] [color=white, fontcolor=white]


	    subgraph cluster_amp {
	    	     label=amp
	    	     amp_in -> amp [dev=amp what="S21"]
		     amp -> amp_out}

	    subgraph cluster_pm_in {
	    	     label=pm_in;
		     pm1_e1;
		     pm2_e1;
		     pmref_e1}

	    subgraph cluster_feedthrough {
	    	     label=feedthrough;
		     msc_in;
		     msc_out}

	    subgraph cluster_msc {
	    	     label=MSC;
		     tuner;
		     fp1;
		     fp2;
		     fp3;
		     fp4;
		     fp5;
		     fp6;
		     fp7;
		     fp8;
		     ant;
		     refant;
		     refant_a1}

	    subgraph cluster_dc {
	    	     label=dc;
		     dc_fwd;
		     dc_rev}

	    subgraph cluster_pmoutput {
	    	     label=pmoutput;
		     pm1;
		     pm2;
		     pmref}

	    subgraph cluster_e_fieldoutput {
	    	     label=e_fieldoutput;
		     field_mon1;
		     field_mon2}

	    sg -> a1 [dev=conn_sg_amp what="S21"] [label=conn_sg_amp]
	    a1 -> amp_in
	    amp_out -> a2
	    a2 -> a21 [dev=cbl_rg214_5m_2003 what="S21"] [label=cbl_rg214_5m_2003]
	    a21 -> msc_in [dev=conn_amp_msc what="S21"] [label=conn_amp_msc]
	    msc_in -> ant [dev=conn_msc_ant what="S21"] [label=cbl_msc_ant]
	    ant -> msc_out [dev=conn_msc_ant what="S21"] [label=cbl_msc_ant]
	    a2 -> dc_fwd [dev=conn_amp_dc_fwd what="S21"] [label=conn_amp_dc_fwd]
	    dc_fwd -> pm1_e1 [dev=conn_dc_fwd_pm1 what="S21"] [label=conn_dc_fwd_pm1]
	    pm1_e1 -> pm1
	    msc_out -> dc_rev [dev=conn_msc_dc_rev what="S21"] [label=conn_msc_dc_rev]
	    dc_rev -> pm2_e1 [dev=conn_dc_rev_pm2 what="S21"] [label=conn_dc_rev_pm2]
	    pm2_e1 -> pm2
	    refant -> refant_a1
	    refant_a1 -> att [dev=conn_refant_att what="S21"] [label=conn_refant_att]
	    att -> pmref_e1 [dev=conn_att_pmref what="S21"] [label=conn_att_pmref]
	    pmref_e1 -> pmref
	    fp1 -> field_mon1
	    fp2 -> field_mon1
	    fp3 -> field_mon1
	    fp4 -> field_mon1
	    fp5 -> field_mon2
	    fp6 -> field_mon2
	    fp7 -> field_mon2
	    fp8 -> field_mon2}




Konﬁgurationsdatei
++++++++++++++++++

Die bei der Kalibrierung verwendete Konﬁgurationsdatei ist im folgenden Listing zu ﬁnden:: 

   import os
   import umdutil

   umdpath=umdutil.getUMDPath()
   dotfile = umdutil.GetFileFromPath('MSC-maincal.dot',umdpath)

   #print dotfile

   cdict = {"autosave_filename": 'msc-autosave.p',
	    "pickle_output_filename": 'msc-maincal.p',
	    "pickle_input_filename": None,
	    "rawdata_output_filename": 'out_raw_maincal-%s.dat',
	    "processeddata_output_filename": 'out_processed_maincal-%s.dat',
	    "after_measurement_pickle_file": 'out_after_maincal_%s.p',
	    "log_filename": 'msc.log',
	    "logger": ['stdlogger'],
	    "minimal_autosave_interval": 1800,
	    "descriptions": ['empty'],
	    "measure_parameters": [{'dotfile': dotfile,
				    'delay': 0.5,
				    'FStart': 200e6,
				    'FStop': 1e9,
				    'SGLevel': -20,
				    'leveling': None,
				    'ftab': [3,6,10,100,1000],
				    'nftab': [20,15,10,20,20],
				    'ntuntab': [[50,18,12,12,12]],
				    'tofftab': [[7,14,28,28,28]],
				    'nprbpostab': [8,8,8,8,8],
				    'nrefantpostab': [8,8,8,8,8],
				    'names': {'sg': 'sg',
					      'a1': 'a1',
					      'a2': 'a2',
					      'ant': 'ant',
					      'pmfwd': 'pm1',
					      'pmbwd': 'pm2',
					      'fp': ['fp1','fp2','fp3','fp4','fp5','fp6','fp7','fp8'], 
					      'tuner': ['tuner'],
					      'refant': ['refant'],
					      'pmref': ['pmref']
					      }
				   }]
	   }



Zunächst werden einige zusätzliche notwendige Module geladen. 

Das Modul :mod:`os` ist ein von Python zur Verfügung gestelltes Modul
zur Zusammenarbeit mit dem Betriebssystem. Das Modul :mod:`umdutil` enthält
nützliche Tools für die Messroutinen und Auswertung und wird vom
Entwicklerteam der Universität Magdeburg bereitgestellt und betreut,
daher auch der Name `uni md utillities`. 

In Zeile 4 wird eine
Umgebungsvariable abgefragt und der Variable *umdpath* zugeordnet. Diese
Umgebungvarable muss unter dem Namen `UMDPATH` auf dem benutzten
Arbeitsplatzrechner eingerichtet werden und enthält alle Pfade, in
denen das Messprogramm nach benötigten Dateien suchern soll, wenn sich
selbige nicht im Messordner beﬁnden oder mit Verweis auf den
vollständigen Pfad übergeben werden. Eine dieser Dateien wäre zum
Beispiel die `.dot` Datei, die in dem Sammelordner für `.dot` Dateien
hinterlegt ist, dessen Pfad ebenfalls in der Umgebungsvariable `UMDPATH`
enthalten sein muss. 

In Zeile 5 sucht dann der Befehl
`umdutil.GetFileFromPath()` aus dem Modul :mod:`umdutil` nach dem übergebenen
Namen der `.dot` Datei (`MSC-maincal.dot`). Diese Suche erfolgt erst im
eigenen Messordner. Falls die Datei dort nicht gefunden wird, werden
die Pfade, die in `UMDPATH` abgelegt sind, der Reihenfolge nach
durchsucht, daher wird ebenfalls die Variable *umdpath* beim
Befehlsaufruf übergeben. Alternativ kann der Name der benötigten
`.dot` Datei auch direkt der Variablen *umdpath* zugewiesen werden. Wenn
sie in einem anderen Ordner als dem Messordner liegt, ist dazu
natürlich die Angabe mit Pfad nötig. 

In Zeile 7 erfolgt Befehl, zur
Kontrolle noch einmal auszugeben, welche `dot` Datei nun für die Messung
verwendet wird. Anschließend wird noch ein Konﬁgurationsblock *cdict*
erzeugt, dass alle festgelegten Parameter, Dateien und Namen enthält
und dann vom aufrufenden Messprogramm ausgewertet bzw. der Instanz der
:class:`MSC` Klasse übergeben wird. Hierbei beﬁnden sich jeweils an erster
Stelle die Namen, die von der Software intern benutzt werden, gefolgt
von den Bezeichnungen, die der Anwender wünscht oder bereits verwendet
hat.

Die Punkte bedeuten im Einzelnen: 

- autosave_ﬁlename ist der Name der Autosave-Datei. 
- pickle_output_ﬁlename ist der Name der auszugebenen pickle-Datei. 
- pickle_input_ﬁlename ist der Name einer schon vorhandenen pickle-Datei, die vor Beginn der Messungen eingelesen werden soll. 
- rawdata_output_ﬁlename ist der Name der Ausgabedatei für die unbehandelten Messdaten. 
- processeddata_output_ﬁlename ist Name der Ausgabedatei für die Ergebnisdaten. 
- after_measurement_pickle_ﬁle bezeichnet den Namen des pickle-ﬁles, das nach Abschluss der Kalibriermessung erstellt wird. 
- log_logﬁlename ist der Name der Datei, die alle Vorgänge während der Messung mitprotokolliert. 
- logger legt die Routine zum Führen der Protokolldatei fest. 
- minimal_autosave_interval ist die minimale Zeitspanne für die Autosaves in Sekunden, im Beispiel also eine halbe Stunde. 
- description ist die Bezeichnung für die aktuelle Messung. 

Anschließend erfolgt die Übergabe der Messparameter für die Instanz der MSC-Klasse. Dabei werden folgende Werte übergeben:

- dotﬁle ist der Name der, den Aufbau charakterisierenden, dot-Datei, welche weiter oben bereits deﬁniert wurde. 
- delay ist eine zusätzliche Verzögerung in Sekunden nach der Positionierung des Rührers, bevor die Messung begonnen wird, um dem Rührer die Gelgenheit zu geben, auszuschwingen o.ä.. 
- FStart ist die Startfrequenz, ab der gemessen wird in Hz. 
- FStop ist die höchste Frequenz in Hz, bei der gemessen wird. 
- SGLevel Ist der Ausgangslevel des Signalgenerators in dBm, bei dem die Messung erfolgt. Dieser Pegel wird in der Regel noch durch den im Messaufbau beﬁndlichen Verstärker erhöht. 
- leveling
- ftab ist eine Liste von Frequenzgrenzen, innerhalb derer eine bestimmte Anzahl von Frequenzen, Tunerpositionen, Feldsondenpositionen und Referenzantennenpositionen zu untersuchen sind. Die Grenzen sind samt der zu untersuchenden Positionen in der Norm nachzulesen. Es wird in den Bereich bis zur dreifachen Startfrequenz 3fs , den Bereich von 3fs bis 6fs , von 6fs bis 10 fs und darüber in Dekaden unterschieden, in denen jeweils eine bestimmte Anzahl von Frequenzen, Tuner- und Messpositionen zu untersuchen sind.- nftab ist die Liste mit der Anzahl der zu untersuchenden Frequenzen pro Abschnitt. 
- ntuntab ist die Liste mit der Anzahl der zu untersuchenden Tunerpositionen pro Abschnitt. 
- tofftab ist die Liste mit der zu benutzenden entsprechenden Tunerschrittweite pro Abschnitt, hier wird in Abstand von 7° und Vielfachen davon gemessen, um die Anzahl der gesamt anzufahrenden Tunerpositionen gering zu halten und so die Messgeschwindigkeit zu optimieren. 
- nprbpostab ist die Liste mit der Anzahl der zu messenden Feldstärken pro Abschnitt. 
- nrefantpostab ist die Liste mit der Anzahl der zu messenden Referenzleistungen pro Abschnitt. 
- names sind die Bezeichnungen der Elemente der Messkette. Hierbei sind die Namen, die
der Anwender für die Elemente in der dot-Datei benutzt, zu übergeben.

Messung
^^^^^^^^

Zum Start der Messung muss man sich im Konsolenmodus beﬁnden. Dazu ruft man über Start Ausführen... die Eingabeaufforderung auf und gibt das Kommando cmd <ENTER> ein. Anschließend wechselt man in der sich öffnenden Konsole in das Verzeichnis des aktuellen Messordners. dort ruft man zum Start in der Umgebung python das Messprogramm, gefolgt vom Konﬁgurationsﬁle, auf. Dies ist in Abbildung 2.3 zu sehen. Alternativ kann die Messung auch durch Doppelklick auf die Batchdatei maincal.bat gestartet werden.

Abbildung 2.3: Aufruf des Messprogramms Während der Messung wird also durch das aufrufende Messprogramm eine Instanz der Klasse MSC erzeugt, der dann die Messparameter übergeben werden und die dann die Messung entsprechend ausführt und auswertet.

2.2.1 Das Messprogramm msc-maincal.py
Das aufrufende Messprogramm ist im Listing 2.3 zu sehen. Diese Datei muss in der Regel nicht geändert werden, da Veränderungen am Messaufbau oder der Messparameter, wie z.B. der zu untersuchende Frequenzbereich durch Änderungen in der dot-Datei bzw. in der Konﬁgurationsdatei dem Messprogramm mitgeteilt werden. Listing 2.3: msc-maincal.py
1 2 3 import o s import s y s import g z i p

16

2 Kalibriermessungen

4 5 6 7 8 9 10 11

import p p r i n t try : import c P i c k l e a s p i c k l e except ImportError : import p i c k l e import MSC import u m d d e v i c e import u m d u t i l

14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 49 50 51 52 53 55 56 57 58 59 60 61 63 64 65 66 67 68 69 70 71 72 73 74 75 76 78

c d i c t = { " a u t o s a v e _ f i l e n a m e " : ’ msc−a u t o s a v e . p ’ , " p i c k l e _ o u t p u t _ f i l e n a m e " : ’ msc−m a i n c a l . p ’ , " p i c k l e _ i n p u t _ f i l e n a m e " : None , " r a w d a t a _ o u t p u t _ f i l e n a m e " : ’ o u t _ r a w _ m a i n c a l−%s . d a t ’ , " p r o c e s s e d d a t a _ o u t p u t _ f i l e n a m e " : ’ o u t _ p r o c e s s e d _ m a i n c a l−%s . d a t ’ , " l o g _ f i l e n a m e " : ’ msc . l o g ’ , " logger " : [ ’ stdlogger ’ ] , " m i n i m a l _ a u t o s a v e _ i n t e r v a l " : 3600 , " d e s c r i p t i o n s " : [ ’ empty ’ , ’ l o a d e d ’ ] , " m e a s u r e _ p a r a m e t e r s " : [ { ’ d o t f i l e ’ : ’ smallMSC−m a i n c a l . d o t ’ , ’ delay ’ : 1 , ’ F S t a r t ’ : 150 e6 , ’ F S t o p ’ : 4 . 2 e9 , ’ SGLevel ’ : −20, ’ l e v e l i n g ’ : None , ’ ftab ’ : [3 ,6 ,10 ,100 ,1000] , ’ nftab ’ : [20 ,15 ,10 ,20 ,20] , ’ ntuntab ’ : [[50 ,18 ,12 ,12 ,12]] , ’ tofftab ’ : [[7 ,14 ,28 ,28 ,28]] , ’ nprbpostab ’ : [8 ,8 ,8 ,8 ,8] , ’ nrefantpostab ’ : [8 ,8 ,8 ,8 ,8] , ’ names ’ : { ’ s g ’ : ’ s g ’ , ’ a1 ’ : ’ a1 ’ , ’ a2 ’ : ’ a2 ’ , ’ ant ’ : ’ ant ’ , ’ pmfwd ’ : ’pm1 ’ , ’pmbwd ’ : ’pm2 ’ , ’ fp ’ : [ ’ fp1 ’ , ’ fp2 ’ , ’ fp3 ’ , ’ fp4 ’ , ’ fp5 ’ , ’ fp6 ’ , ’ fp7 ’ , ’ fp8 ’ ] , ’ tuner ’ : [ ’ tuner1 ’ ] , ’ refant ’ : [ ’ refant1 ’ ] , ’ pmref ’ : [ ’ pmref1 ’ ] } }] } d e f myopen ( name , mode ) : i f name [ −3:] == ’ . gz ’ : r e t u r n g z i p . open ( name , mode ) else : r e t u r n f i l e ( name , mode ) def update_conf ( c d i c t ) : try : import c o n f i g c d i c t . update ( config . c d i c t ) p r i n t " C o n f i g u r a t i o n u p d a t e d from ’ c o n f i g . py ’ . " except ImportError : pass i f l e n ( s y s . a r g v ) >1: f o r name i n s y s . a r g v [ 1 : ] : try : _mod = _ _ i m p o r t _ _ ( name [ : name . r i n d e x ( ’ . ’ ) ] ) c d i c t . u p d a t e ( g e t a t t r ( _mod , ’ c d i c t ’ ) ) p r i n t " C o n f i g u r a t i o n u p d a t e d from ’% s ’ . "%name except : try : d c t = e v a l ( name ) i f t y p e ( d c t ) == t y p e ( { } ) : c d i c t . update ( dct ) p r i n t " C o n f i g u r a t i o n u p d a t e d from ’% s ’ . "%s t r ( d c t ) except : pass d e f l o a d _ f r o m _ a u t o s a v e ( fname ) :

17

2 Kalibriermessungen

79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130 131

msc=None cmd=None i f o s . p a t h . i s f i l e ( fname ) : try : p f i l e = myopen ( fname , " r b " ) msc= p i c k l e . l o a d ( p f i l e ) cmd=msc . ascmd i f msc : msg = " Auto s a v e f i l e %s f o u n d . \ ncmd : %s \ n \ nResume : Resume Measurement \ nNew : S t a r t new . " %(fname , cmd ) b u t = [ " Resume " , "New" ] a n s w e r = msc . m e s s e n g e r ( msg , b u t ) # a n s w e r =0 i f a n s w e r == b u t . i n d e x ( ’ Resume ’ ) : startnew = False else : d e l msc d e l cmd msc=None cmd=None e x c e p t I O E r r o r , m: # t h i s i s no p r o b l e m msc . m e s s e n g e r ( " I O E r r o r d u r i n g c h e c k f o r a u t o s a v e−f i l e : %s \ n C o n t i n u e w i t h n o r m a l o p e r a t i o n . . . "%m, [ ] ) e x c e p t ( U n p i c k l i n g E r r o r , A t t r i b u t e E r r o r , EOFError , I m p o r t E r r o r , I n d e x E r r o r ) , m: # u n p i c k l e was n o t s u c c e s f u l , b u t we w i l l c o n t i n u e anyway # u s e r can d e c i d e l a t e r except : # r a i s e a l l unhadled e x c e p t i o n s raise r e t u r n msc , cmd d e f m a k e _ l o g g e r _ l i s t ( msc , c l o g g e r ) : logger = [] for _l in clogger : _ l s t = _l . s p l i t ( ’ . ’ ) _mod=None i f l e n ( _ l s t ) ==1: # no module g i v e n _mod = msc e l i f l e n ( _ l s t ) ==2: try : _mod = _ _ i m p o r t _ _ ( _ l s t [ 0 ] ) e x c e p t I m p o r t E r r o r , m: _mod = None msc . m e s s e n g e r ( " I m p o r t E r r o r : %s "%m, [ ] ) i f _mod : try : l o g g e r . a p p e n d ( g e t a t t r ( msc , _ l ) ) e x c e p t A t t r i b u t e E r r o r , m: msc . m e s s e n g e r ( " L o g g e r n o t f o u n d : %s "%m, [ ] ) i f not l e n ( l o g g e r ) : return logger [ : ] # empty l o g g e r = [ msc . s t d l o g g e r ] # f a l l b a c k t o s t d l o g g e r # _ l s t can be e . g . [ s t d l o g g e r ] o r [ custom , F i l e t a b l o g g e r ] i f he want t o f i n i s h . msc . m e s s e n g e r ( " E r r o r d u r i n g u n p i c k l e o f a u t o s a v e−f i l e : %s \ n C o n t i n u e w i t h n o r m a l o p e r a t i o n . . . "%m, [ ] )

134 136 137 138 139 141 143 144 145 146 147 148 149 150 151 152 153

i f __name__ == ’ __main__ ’ : update_conf ( cdict ) print " Configuration values : " print pprint . pprint ( cdict ) msc , cmd= l o a d _ f r o m _ a u t o s a v e ( c d i c t [ ’ a u t o s a v e _ f i l e n a m e ’ ] ) i f n o t msc : if cdict [ ’ pickle_input_filename ’ ]: p f i l e = myopen ( c d i c t [ ’ p i c k l e _ i n p u t _ f i l e n a m e ’ ] , " r b " ) p r i n t " L o a d i n g i n p u t p i c k l e f i l e ’% s ’ . . . "%c d i c t [ ’ p i c k l e _ i n p u t _ f i l e n a m e ’ ] msc= p i c k l e . l o a d ( p f i l e ) pfile . close () p r i n t " . . . done " else : msc=MSC.MSC ( ) msc . s e t L o g F i l e ( c d i c t [ ’ l o g _ f i l e n a m e ’ ] ) l o g g e r = m a k e _ l o g g e r _ l i s t ( msc , c d i c t [ ’ l o g g e r ’ ] )

18

2 Kalibriermessungen

154 155 156 158 159 160 161 162 163 164 165 166 167 168 169 170 171 172 173 174 175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190 191 192 193 194 195 196 197 198 199 200 201 202 203 204 205 206 207 208 209 210 211 212 213 214 215 216 218 219 220 221 222 223 224 225 226 227

msc . s e t L o g g e r ( l o g g e r ) msc . s e t A u t o S a v e ( c d i c t [ ’ a u t o s a v e _ f i l e n a m e ’ ] ) msc . S e t A u t o S a v e I n t e r v a l ( c d i c t [ ’ m i n i m a l _ a u t o s a v e _ i n t e r v a l ’ ] ) descriptions = cdict [ ’ descriptions ’ ][:] for _i , _des in enumerate ( c d i c t [ ’ d e s c r i p t i o n s ’ ] ) : try : mp = c d i c t [ ’ m e a s u r e _ p a r a m e t e r s ’ ] [ _ i ] except IndexError : mp = c d i c t [ ’ m e a s u r e _ p a r a m e t e r s ’ ] [ 0 ] mp [ ’ d e s c r i p t i o n ’ ] = _ d e s domeas= T r u e d o e v a l =True i f msc . r a w D a t a _ M a i n C a l . h a s _ k e y ( _ d e s ) : domeas= F a l s e doeval=False msg = " " " " Measurement w i t h d e s c r i p t i o n ’%s ’ a l l r e a d y f o u n d i n MSC i n s t a n c e . \ n How do you want t o p r o c e e d ? \ n \ n C o n t i n u e : C o n t i n u e w i t h Measurement . \ n S k i p : S k i p Measurement b u t do E v a l u a t i o n . \ n B r e a k : S k i p Measurement and E v a l u a t i o n . \ n Exit : Exit Application " " " %( _ d e s ) but = [ " Continue " , " Skip " , " Break " , " E x i t " ] a n s w e r = msc . m e s s e n g e r ( msg , b u t ) # a n s w e r =0 i f a n s w e r == b u t . i n d e x ( ’ B r e a k ’ ) : continue e l i f a n s w e r == b u t . i n d e x ( ’ E x i t ’ ) : sys . e x i t ( ) e l i f a n s w e r == b u t . i n d e x ( ’ C o n t i n u e ’ ) : domeas= T r u e d o e v a l =True e l i f a n s w e r == b u t . i n d e x ( ’ S k i p ’ ) : domeas= F a l s e d o e v a l =True else : # be s a v e and do n o t h i n g continue i f domeas : msc . Measure_MainCal (∗∗mp ) p i c k l e . dump ( msc , f i l e ( c d i c t [ " a f t e r _ m e a s u r e m e n t _ p i c k l e _ f i l e " ]% _des , ’wb ’ ) , 2 ) i f doeval : msc . OutputRawData_MainCal ( fname = c d i c t [ " r a w d a t a _ o u t p u t _ f i l e n a m e " ]% _ d e s ) msc . E v a l u a t e _ M a i n C a l ( d e s c r i p t i o n = _ d e s ) f o r _ p a s s e d c a l in c d i c t [ ’ d e s c r i p t i o n s ’ ] [ : c d i c t [ ’ d e s c r i p t i o n s ’ ] . index ( _des ) ] : msc . C a l c u l a t e L o a d i n g _ M a i n C a l ( e m p t y _ c a l = _ p a s s e d c a l , l o a d e d _ c a l = _ d e s ) d e s c r i p t i o n s . a p p e n d ( "%s+%s " %( _ p a s s e d c a l , _ d e s ) ) msc . O u t p u t P r o c e s s e d D a t a _ M a i n C a l ( fname = c d i c t [ " p r o c e s s e d d a t a _ o u t p u t _ f i l e n a m e " ]%( " _ " . j o i n ( d e s c r i p t i o n s ) ) ) else : msg= " S e l e c t d e s c r i p t i o n t o u s e . \ n " but = [ ] f o r _i , _des i n enumerate ( c d i c t [ ’ d e s c r i p t i o n s ’ ] ) : msg+=’%d : %s ’%( _ i , _ d e s ) b u t . a p p e n d ( ’% d : %s ’%( _ i , _ d e s ) ) a n s w e r =msc . m e s s e n g e r ( msg , b u t ) try : mp = c d i c t [ ’ m e a s u r e _ p a r a m e t e r s ’ ] [ a n s w e r ] except IndexError : mp = c d i c t [ ’ m e a s u r e _ p a r a m e t e r s ’ ] [ 0 ] mp [ ’ d e s c r i p t i o n ’ ] = c d i c t [ ’ d e s c r i p t i o n s ’ ] [ a n s w e r ] e x e c ( cmd ) i f os . pa th . i s f i l e ( c d i c t [ ’ p i c k l e _ o u t p u t _ f i l e n a m e ’ ] ) : msg = " P i c k l e f i l e %s a l l r e a d y e x i s t . \ n \ n O v e r w r i t e : O v e r w r i t e f i l e \ nAppend : Append t o f i l e . " %( c d i c t [ ’ pickle_output_filename ’]) b u t = [ " O v e r w r i t e " , " Append " ] a n s w e r = msc . m e s s e n g e r ( msg , b u t ) i f a n s w e r == b u t . i n d e x ( ’ O v e r w r i t e ’ ) : mode = ’wb ’ else : mode = ’ ab ’ else : mode = ’wb ’

19

2 Kalibriermessungen

228 229 230 231 232 233 234 235 236 237 238 239 240 241

try : msc . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " p i c k l e r e s u l t s t o ’%s ’ . . . " %( c d i c t [ ’ p i c k l e _ o u t p u t _ f i l e n a m e ’ ] ) , [ ] ) p f = myopen ( c d i c t [ ’ p i c k l e _ o u t p u t _ f i l e n a m e ’ ] , mode ) p i c k l e . dump ( msc , pf , 2 ) msc . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " . . . done . " , [ ] ) except : msc . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " f a i l e d t o p i c k l e t o %s " %( c d i c t [ ’ p i c k l e _ o u t p u t _ f i l e n a m e ’ ] ) , [ ] ) raise else : # remove a u t o s a v e f i l e try : o s . remove ( c d i c t [ ’ a u t o s a v e _ f i l e n a m e ’ ] ) except : pass a f t e r m e a s u r e m e n t i s c o m p l e t e d and c l a s s i n s t a n c e was p i c k l e d

Zunächst werden wieder einige Module und plug-ins importiert. Das Modul pickle bzw. cpickle ist zur Erzeugung der pickle-Dateien erforderlich. MSC und umddevice sind an der Universität Magdeburg programmierte Module zur Durchführung der einzelnen Messroutinen bzw. zur Kommunikation mit den Messgeräten. Danach erfolgt die Vorbelegung der Variablen des dictionaries mit default-Werten. Diese werden dann später ggf. beim Einladen des Konﬁgurationsﬁles aktualisiert. Anschließend werden einige Routinen deﬁniert. Die Routine myopen liefert bei Aufruf die in der Variable name geforderte Datei zurück, sollte sie gepackt sein, wird sie vorher noch entpackt. Durch update_conf wird ein Update des Koﬁgurationsdictionaries durchgeführt, die bisherigen Einträge in dict also gegebenfalls durch neue Einträge ersetzt, die, in Abhängigkeit von der aufrufenden Routine, aus einer Autosavedatei, einer geladen pickle-Datei oder auch aus der mit dem Messprogramm aufgerufenen Konﬁgurationsdatei stammen können. Durch die Routine load_from_autosave wird eine Autosavedatei geladen. make_logger_list stellt eine Liste von für Protokolldateien zuständigen Routinen zur Verfügung. Dann beginnt in Zeile 133 das eigentliche Programm. Zunächst wird ein Update der Messvariablen durchgeführt und diese dann anschließend ausgegeben. Dann versucht das Messprogramm, eine Instanz der Klasse MSC zu erstellen. Hierzu wird zunächst mit Hilfe der Routine load_from_autosave überprüft, ob bereits eine Autosavedatei unter dem im Koﬁgurationsblockcdict angegebenen Namen existiert. Gibt es diese Autosavedatei, wird abgefragt, ob sie eingelesen werden soll und bei Bestätigung in Zeile 141 nach dem Einlesen der Daten der Autosavedatei die gespeicherte Instanz der Klasse MSC wieder erstellt. Der zweite zurückgelieferte Wert cmd liefert das Kommando zurück, das die Routine aufrief, in der die Autosavedatei erstellt wurde, also die Routine, die bei Speicherung der Daten gerade lief. Anschließend wird in Zeile 205 abgefragt, welche der unter verschiedenen Bezeichnungen abgespeicherten Messungen man verwenden möchte. Anschließend werden die aktuellen Messparameter mp übergeben und in Zeile 216 die gespeicherte begonnene Messung mit dem erneuten Aufruf der in cmd gespeicherten letzten aufgerufenen Routine an der gesicherten Stelle weitergeführt. Gibt es keine Autosavedatei unter dem angegebenen Namen oder

20

2 Kalibriermessungen soll diese nicht benutzt werden, wird der Messordner nach dem im cdict angegebenen pickle-ﬁle durchsucht und dieses geladen. In diesem Fall würde dann aus den in der pickle-Datei enthaltenen Daten die Instanz der Klasse MSC wieder erzeugt werden. Anschließend werden ab Zeile 152 dieser Instanz die Konﬁgurationen und die measurement_parameters aus dem cdict übergeben. Nun wird untersucht, ob in dieser Instanz bereits Messungen unter der description abgelegt sind, die für die aktuelle Messung laut Konﬁgurationsdatei benutzt werden sollen. Dies kann natürlich nur beim Laden eines alten pickle-ﬁles der Fall sein. Wird eine Messung gefunden, wird diese mit der entsprechenden description ausgegeben und in Zeile 172 abgefragt, wie weiter zu verfahren ist. Es besteht die Möglichkeit, die aktuelle Messung weiterzuführen (Continue). Weiterhin kann die aktuelle Messung abgebrochen und mit der Auswertung der vorhandenen Daten fortgefahren werden (Skip). Es ist ebenfalls möglich, sowohl die aktuelle Messung als auch die Auswertung abzubrechen (Break) oder das Messprogramm komplett zu beenden (Exit). Wird ein Fortsetzen der Messungen gewählt, würde der alte Datensatz aus dem pickleﬁle überschrieben werden und die Routine msc.Measure_MainCal führt die Messung mit den in mp übergebenen Messparametern vom Zeitpunkt der erfolgten Sicherung an fort. Anschließend, bzw. wenn nur die Auswertung der Daten ausgewählt wurde, erfolgt in Zeile 198 erst durch die Routine msc.OutputRawData_MainCal die Ausgabe der Rohdaten in die im Konﬁgurationsblock cdict unter rawdata_output_ﬁlename angegebene Datei, anschließend durch die Routine msc.Evaluate_MainCal die Auswertung der Daten. Dabei wird überprüft sind Konﬁgurationsblock mehrere descriptions enthalten, wird überprüft, ob bereits Messungen mit anderen Bezeichnungen fertig sind und falls vorhanden die Datensätze der Messungen auch miteinander ausgewertet. Das wäre typischerweise der Fall, wenn die Kalibrierung der leeren und beladenen Kammer gleich innerhalb einer Messung durchgeführt wird, als Bezeichnungen könnten dann zum Beispiel empty und loaded gewählt werden. Dann könnte anschließend durch die Funktion msc.CalculateLoading_MainCal in Zeile 201 gleich das Loading der Kammer berechnet werden. Anschließend erfolgt in Zeile 203 durch die Routine msc.OutputProzessedData_MainCal die Ausgabe der ausgewerteten und geordneten Daten in die im Konﬁgurationsblock cdict unter prozesseddata_output_ﬁlename angegebene Datei. Sollten keine Sicherungsdateien vorhanden oder gewünscht werden, wird die eine neue Instanz der Klasse MSC erstellt und eine neue Messung mit den eben angesprochenen Routinen der Klasse MSC begonnen und anschließend ausgewertet. Diese Messung erhält dann als Bezeichnung den ersten Eintrag der Liste descriptions aus dem Konﬁgurationsblock. Die Messung wird dann für alle weiteren in description eingetragenen Bezeichnungen wiederholt. Nachdem mit der Ausgabe der Daten die Auswertung abgeschlossen ist, wird eine abschließende pickle-Datei angelegt, die alle bisherigen Messungen dieser Instanz der Klasse enthält, also die soeben beendete Messung samt Auswertung, sowie die, die in einer evtl. zuvor ein-

21

2 Kalibriermessungen gelesen Sicherungsdatei (Input-pickle-Datei oder autosavedatei) gespeichert waren. Der Name dieser Output-pickle-Datei wurde ebenfalls in der Konﬁgurationsdatei festgelegt. Zunächst wird in Zeile 218 geprüft, ob es bereits eine Datei unter diesem Namen gibt. Falls das der Fall ist, wird abgefragt, ob diese evtl. überschrieben werden soll, oder ob die neue pickle-Datei einfach an die vorhandene Datei angehängt werden soll. Nachdem die komplette Messung als Outputpickle-Datei gesichert wurde, wird letzlich noch die evtl. vorhanden Autosavedatei gelöscht, da sie ja durch die beendete Messung und Auswertung nicht benötig wird. Achtung: Wird die Messung aus einer Autosavedatei gestartet, wird nach Abschluss der Messung keine Auswertung ausgeführt, sondern nur das Output-pickle-ﬁle erstellt. In diesem Fall muss die Messung mit diesem Output-pickle-ﬁle als Input-pickle-ﬁle nocheinmal gestartet werden. Dann würde, wie oben beschrieben, die Meldung, dass im eingelesenen pickle-ﬁle bereits eine Messung mit der aktuellen description vorhanden ist und die Abfrage, was geschehen soll, erscheinen. Durch Auswahl von Skip wird dann die aktuelle Messung abgebrochen und es werden nur die vorhandenen Daten aus der gespeicherten Messung ausgewertet und man erhält so die Roh- und Ergebnisdaten. Das Messprogramm kann während der Messung jederzeit durch Drücken einer Taste gestoppt werden. Dies wird auch akustisch signalisiert. Der Ausgangssignal des Signalgenerators wird abgeschaltet, die Kammer kann also geöffnet und auch betreten werden. Gleichzeitig erfolgt eine Abfrage, wie weiter zu verfahren ist. Mit Continue kann die Messung fortgesetzt werden. Mit Suspend werden die Geräte vom Bus abgemeldet, die Instanz bleibt jedoch aktiv, da das Messprogramm auf weitere Eingaben wartet. Die Geräte können ausgeschaltet und auch aus dem Aufbau entfernt werden. Dies kann zum Beispiel genutzt werden, um die Akkus der Sonden zu laden oder Geräte kurzzeitig für andere Messungen zu benutzen, ohne dafür das Messprogramm unterbrechen zu müssen. Der Rechner darf jedoch während dieser Zeit nicht ausgeschaltet werden, da das Messprogramm ja noch läuft. Nachdem alle Geräte wieder angeschlossen und eingeschaltet sind, kann die Messung fortgesetzt werden. Hierzu werden alle Geräte neu initialisiert und die Messung läuft weiter. Mit Quit kann die Messung auch beendet werden. Abbildung 2.4 zeigt den Inhalt des Messordners nach Abschluss der Messung.

22

2 Kalibriermessungen

Abbildung 2.4: Messordnerinhalt nach Abschluss der Kalibriermessung

23

3 Messungen zur Untersuchung der Störfestigkeit
Der Ablauf einer typischen Störfestigkeitsmessung soll am Beispiel der Störschwellenuntersuchung an Einplatinen-Industrie-PCs erläutert werden. Bei dieser Untersuchung kamen die in Abbilding 3.1 gezeigten Industrie-PC-Boards der Firma ICP zum Einsatz. Die Messungen erfolgten im stirred-mode der Kammer, also bei einem sich kontinuierlich drehenden Rührer.

Abbildung 3.1: untersuchte PC-Boards Während der Untersuchungen lief auf den PCs jeweils ein Testprogramm, welches periodisch ein Bit des Parallelports kippte und so ein Rechtecksignal auf der Parallelschnittstelle ausgab. Dieses Testprogramm ist auf einem Flash-RAM auf dem Board gespeichert. Von der Parallelschnittstelle des Boards wurde dieses Signal über eine Lichtwellenleiterverbindung an eine Auswertebox, die außerhalb der Modenverwirbelungskammer steht, geleitet. In dieser Box wurde das Signal ausgewertet und konnte dann mit Hilfe eines Oszilloskops betrachtet werden. Über eine zweite Lichtwellenleiterverbindung der Box mit dem Board konnte der Rechner nach einem durch eine Störung (zu hohe Feldstärke) verursachter Ausfall durch Drücken eines

24

3 Messungen zur Untersuchung der Störfestigkeit RESET-Knopfes an der Box von Hand neu gestartet werden, falls er nicht von selbst neu bootete. In einigen Fällen konnte es auch vorkommen, dass selbst ein extern ausgelöstes Reset den Rechner nicht zu einem Neustart bewegen konnte, da entweder das Testprogramm beschädigt wurde und neu aufgespielt werden musste oder einfach die zur Energieversorgung dienenden Akkus leer waren und ersetzt werden mussten. Es wurde während der Messung zwischen 3 unterschiedlichen Rechnerausfallarten unterschieden: • Ausfall mit selbständigem Neustart des Rechners • Ausfall mit notwendigem externen RESET zum Rechnerneustart • Beschädigung des Testprogramms

3.1 Messablauf
Der Prüﬂing sollten während der Untersuchung mit cw-Signalen sowie mit pulsmodulierten Signalen unter Variation der Pulsparameter beaufschlagt werden.
Modenverwirbelungskammer LWL GPIB

MC
Referenzantenne Sendeantenne

PM

EUT

PM PM

RK
Verstärker

Box
Signalgenerator

Oszilloskop

Messrechner

Abbildung 3.2: Schematischer Aufbau der Messung In Abbildung 3.2 ist der prinzipielle Aufbau der Messung dargestellt. Während der Messung

25

3 Messungen zur Untersuchung der Störfestigkeit wurde jeweils der zu untersuchende Frequenzbereich in Schritten von je 50 MHz durchfahren. Bei jeder Frequenz begann die Messung bei einer Feldstärke von 100 V/m. Jeweils nach einer vollen Umdrehung des Rührers im mode-stirred-Betrieb, bzw. nach dem Anfahren einer neuen Tunerposition im mode-tuned-Betrieb wurde das Ausgangssignal des PC-Boards überprüft. Wurde das Testsignal detektiert, lief der Rechner also noch anstandslos, wurde die Feldstärke um 10 V/m erhöht. Um die Boards und das Messequipment im Inneren der Kammer vor Zerstörung zu schützen, wurde die maximale Testfeldstärke auf 1000 V/m begrenzt. Dies war nötig, da sich bei vergangenen Messungen zeigte, dass bei noch höheren Feldstärken die in den Leiterbahnen induzierten Ströme so groß werden, daß durch die entsprechende Hitzewirkung das Equipment mechanisch zerstört werden kann. Sollte ein Ausfall des Rechners festgestellt werden, wurde, wie bereits angedeutet, zwischen verschiedenen Störungen unterschieden. Fuhr der PC selbständig wieder hoch, wurde ein interner RESET notiert. War zum Neustart des Rechners ein RESET-Impuls über den Lichtwellenleiter notwendig, wurde vom externen RESET gesprochen. Konnte das Testsignal auch nach einem externen RESET nicht detektiert werden, mussten entweder neue geladene Akkus angeschlossen werden, dies wurde dann selbstverständlich nicht als Fehler detektiert, sondern die Messung wured in diesem Fall bei dieser Frequenz wiederholt. In einigen Fällen wurde allerdings das Testprogramm auf den Boards zerstört und musste an einem gesonderten Rechner neu eingespielt werden. In diesem Fall wurde ein User-RESET aufgezeichnet.

3.2 Vorbereitungen
Zunächst stellte sich aus Efﬁziensgründen die Aufgabe, die Überwachung des Prüﬂings und, falls erforderlich, den Neustart des PCs zu automatisieren und in den Messablauf zu integrieren. Hierzu wurde zunächst die Überwachung des durch das Testprogramm erzeugten Ausgangssignals mit Hilfe eines Oszilloskops TDS420 der Firma Tektronix durch die Messsoftware realisiert. Während der Messung wird ständig die Amplitude des Signals während der Einschalt- und Ausschaltzeit sowie die Periodendauer des Signals gemessen und mit vorgegebenen Schwellwerten verglichen. Diese Messung erfolgt immer nach einem kompletten Rührerumlauf. Wird einer der Schwellwerte überschritten, wird das Ereignis als Ausfall markiert. Das Messprogramm stoppt für einen gewissen Zeitraum, nach einigen Tests hat sich eine Zeitspanne von 25 Sekunden als ausreichend erwiesen, um dem Rechner die Möglichkeit zu geben, selbstständig neu zu booten. Nach Ablauf dieser Zeit wird das Ausgangssignal erneut überprüft. Sollte es immer noch nicht vorhanden sein, wird ein RESET über die Lichtwellenleiterverbindung aus-

26

3 Messungen zur Untersuchung der Störfestigkeit gelöst und abermals eine eine gewisse Zeit gewartet. Sollte das Signal dann immer noch nicht anliegen, stoppt die Messung mit einer optischen und akustischen Meldung an den Benutzer. Dieser hat dann die Möglichkeit, zu überprüfen, ob die Akkus leer sind und neu aufgeladen werden müssen oder ob ein Fehler am Board aufgetreten ist und das Testprogramm neu aufgespielt werden muss. Weiterhin wurde die RESET-Auslösung über die Lichtwellenleiterverbindung automatisiert. Hierzu wurde die Schaltung in der Auswertebox etwas modiﬁziert. Es wurde eine identische Laserdiode über einen Vorwiderstand direkt mit dem Parallelport des Messplatzrechners verbunden. Zur RESET-Auslösung wird das entsprechende Bit des Parallelports kurz auf „high“-Potential geschaltet und somit der RESET-Impuls ausgelöst. Da es unter dem Betriebssystem Windows XP nicht mehr ohne weiteres möglich ist, auf die externen Schnittstellen des Rechners zuzugreifen, war zusätzliche Software nötig, um dies dennoch zu ermöglichen. Diese Programmbibliothek wurde dann ebenfalls als Teil eines Programms in die Softwareumgebung eingebunden. Wie bereits angesprochen, ist es günstiger, für jede Messung einen gesonderten Ordner zu benutzen, um in diesem alle Daten zu speichern. In dieses Ordner gehören jeweils die Konﬁgurationsdatei, das aufrufende Messprogramm und evtl. die entsprechende .dot-Datei. In Abbildung 3.3 ist ein Beispiel für den Inhalt eines Messordners zu sehen. Zusätzlich beﬁndet sich im Ordner noch eine Textdatei mit dem Namen info.txt, in der Anmerkungen, Besonderheiten und anderes Wissenswertes zur jeweiligen Messungen notiert werden können sowie 2 ...eval.pyDateien, die zur weiteren Bearbeitung der Messwerte dienen.

Abbildung 3.3: Messordnerinhalt vor Beginn der Messung

3.2.1 Die dot-Datei
Wie bereits erwähnt, wurde während der Messreihe immer der selbe Messaufbau benutzt. Daher wurde die dot-Datei zentral im Sammelordner für dot-Dateien abgelegt und von dort aufgerufen.

27

3 Messungen zur Untersuchung der Störfestigkeit Sie ist im Listing 3.1 dargestellt. Listing 3.1: .dot-Datei des Beispiels
1 2 3 4 5 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 24 25 26 27 } digraph { node [ f o n t s i z e = 2 4 ] ; graph [ f o n t s i z e =24]; edge [ f o n t s i z e = 2 0 ] ; r a n k d i r =LR ; c b l _ s g _ a m p [ i n i = "M: \ \ umd−c o n f i g \ \ smallMSC \ \ i n i \ \ c b l _ s g _ a m p . i n i " c o n d i t i o n = " 10 e6 <= f <= 18 e9 " ] [ c o l o r = w h i t e , f o n t c o l o r = w h i t e ] c b l _ a m p _ a n t [ i n i = "M: \ \ umd−c o n f i g \ \ smallMSC \ \ i n i \ \ c b l _ a m p _ a n t . i n i " c o n d i t i o n = " 10 e6 <= f <= 4 . 2 e9 " ] [ c o l o r = w h i t e , f o n t c o l o r = white ] cbl_amp_pm1 [ i n i = "M: \ \ umd−c o n f i g \ \ smallMSC \ \ i n i \ \ cbl_amp_pm1 . i n i " c o n d i t i o n = " 10 e6 <= f <= 4 . 2 e9 " ] [ c o l o r = w h i t e , f o n t c o l o r = white ] sg amp ant [ i n i = "M: \ \ umd−c o n f i g \ \ smallMSC \ \ i n i \ \ umd−g t −12000A e a l . i n i " ] [ s t y l e = f i l l e d , c o l o r = l i g h t g r e y ] −r [ i n i = "M: \ \ umd−c o n f i g \ \ smallMSC \ \ i n i \ \ umd−a r −100s1g4−3dB−r e a l −r e m o t e . i n i " c o n d i t i o n = " 800 e6 <= f <= 4 . 2 e9 " ] [ i n i = "M: \ \ umd−c o n f i g \ \ smallMSC \ \ i n i \ \ umd−r s−HF906_04 . i n i " ] [ s t y l e = f i l l e d , c o l o r = l i g h t g r e y ] [ i n i = "M: \ \ umd−c o n f i g \ \ smallMSC \ \ i n i \ \ umd−r s−HF906_03 . i n i " ] [ s t y l e = f i l l e d , c o l o r = l i g h t g r e y ]

refant

t u n e r [ i n i = "M: \ \ umd−c o n f i g \ \ smallMSC \ \ i n i \ \ umd−sms60−r e a l . i n i " ch = 1 ] [ s t y l e = f i l l e d , c o l o r = l i g h t g r e y ] p m r e f [ i n i = "M: \ \ umd−c o n f i g \ \ smallMSC \ \ i n i \ \ umd−r s−nrvd−2 e a l . i n i " ch = 2 ] [ s t y l e = f i l l e d , c o l o r = l i g h t g r e y ] −r pm1 pm2 [ i n i = "M: \ \ umd−c o n f i g \ \ smallMSC \ \ i n i \ \ umd−r s−nrvd−1 e a l . i n i " ch = 1 ] [ s t y l e = f i l l e d , c o l o r = l i g h t g r e y ] −r [ i n i = "M: \ \ umd−c o n f i g \ \ smallMSC \ \ i n i \ \ umd−r s−nrvd−1 e a l . i n i " ch = 2 ] [ s t y l e = f i l l e d , c o l o r = l i g h t g r e y ] −r white ] c b l _ r _ p m r [ i n i = "M: \ \ umd−c o n f i g \ \ smallMSC \ \ i n i \ \ c b l _ r _ p m r . i n i " c o n d i t i o n = " 10 e6 <= f <= 18 e9 " ] [ c o l o r = w h i t e , f o n t c o l o r = w h i t e ] a t t 2 0 [ i n i = "M: \ \ umd−c o n f i g \ \ smallMSC \ \ i n i \ \ a t t 2 0 −50 i n i " c o n d i t i o n = " 10 e6 <= f <= 18 e9 " ] [ c o l o r = w h i t e , f o n t c o l o r = w h i t e ] W. a1 [ s t y l e = f i l l e d , c o l o r = l i g h t g r e y ] a2 [ s t y l e = f i l l e d , c o l o r = l i g h t g r e y ] subgraph cluster_amp { l a b e l =amp amp_in −> amp_out [ dev =amp what = " S21 " ]

c b l _ a n t _ p m 2 [ i n i = "M: \ \ umd−c o n f i g \ \ smallMSC \ \ i n i \ \ c b l _ a n t _ p m 2 . i n i " c o n d i t i o n = " 10 e6 <= f <= 4 . 2 e9 " ] [ c o l o r = w h i t e , f o n t c o l o r =

30 31 32 33 34 35 36 37 39 41 43

sg−>a1 [ dev = c b l _ s g _ a m p what = " S21 " ] [ l a b e l = " c b l _ s g _ a m p " ] a1−>amp_in amp_out−>a2 a2−>a n t [ dev = c b l _ a m p _ a n t what = " S21 " ] a2−>pm1 [ dev =cbl_amp_pm1 what = " S21 " ] f e e d t h r u −>p m r e f [ dev = a t t 2 0 what = " S21 " ] a n t −>pm2 [ dev = c b l _ a n t _ p m 2 what = " S21 " ] [ l a b e l =" cbl_amp_ant " ] [ l a b e l = " cbl_amp_pm1 " ] [ l a b e l =" cbl_r_pmr " ] [ l a b e l =" a t t 2 0 " ] [ l a b e l =" cbl_ant_pm2 " ]

r e f a n t −>f e e d t h r u [ dev = c b l _ r _ p m r what = " S21 " ]

s u b g r a p h " c l u s t e r _ m s c " { l a b e l =MSC; a n t ; r e f a n t } s u b g r a p h " c l u s t e r _ p m o u t p u t " { l a b e l = " o u t p u t " ; pm1 ; pm2 ; p m r e f ; } }

Der daraus resultierende Aufbau ist in Abbildung 3.4 zu sehen.

3.2.2 Konﬁgurationsdatei
Kommen wir nun zur Konﬁgurationsdatei conf_pcboad1.py, welche im Listing 3.2 zu sehen ist. Listing 3.2: Konﬁgurationsdatei des Beispiels
1 2 3 import o s import u m d u t i l import s c i p y

28

3 Messungen zur Untersuchung der Störfestigkeit
att20 cbl_r_pmr cbl_ant_pm2 tuner amp sg cbl_amp_pm1 cbl_amp_ant cbl_sg_amp
cbl_sg_amp cbl_amp_ant

MSC ant refant
cbl_r_pmr cbl_amp_pm1 cbl_ant_pm2 att20

output pm2 pmref pm1

amp a1 amp_in amp_out a2

feedthru

Abbildung 3.4: Messaufbau des Beispieles
4 6 7 8 10 12 14 15 16 17 18 19 20 21 22 24 26 27 28 30 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 import I m m u n i t y T h r e s h o l d T D S 4 a s I m m u n i t y T h r e s h o l d umdpath = u m d u t i l . getUMDPath ( ) d o t f i l e = u m d u t i l . G e t F i l e F r o m P a t h ( ’ smallMSC−immunity−no−f p . d o t ’ , umdpath ) p r i n t ’DOTFILE : ’ , d o t f i l e t e s t f r e q s = s c i p y . a r a n g e ( 3 . 3 e9 , 3 . 8 5 e9 , 5 0 e6 ) . t o l i s t ( ) f i e l d =range (100 ,1010 ,10) kern el = ImmunityThreshold . ImmunityKernel_Thres # k p a r s = { ’ t p ’ : None , ’ f i e l d ’ : f i e l d , ’ d w e l l ’ : 1 , ’ t e s t f r e q s ’ : t e s t f r e q s } k p a r s = { ’ t p ’ : None , ’ field ’ : field , ’ dwell ’ : 3 , ’ testfreqs ’ : testfreqs , ’ what ’ : { 6 : ( 2 0 0 e3 , 4 0 0 e3 ) , 7 : ( 3 . 5 , 4 . 5 ) , 8 : ( − 0 . 5 , 0 . 5 ) } , ’ PMfreq ’ : 1 e6 , ’ PMduty ’ : 15} print kernel , kpars t h e b o a r d = ’ PCBoard1 ’ m a i n c a l = ’ I : \ \ Messungen \ \ smallMSC \ \ c a l −4−05\\msc−m a i n c a l−l o a d i n g . p ’ e u t c a l = ’M: \ \ t e s t i n g \ \ e u t c a l \ \ b o a r d 0 1 \ \ msc−e u t c a l −w i t h−l o a d i n g . p ’ cal =maincal c d i c t = { " a u t o s a v e _ f i l e n a m e " : ’ msc−a u t o s a v e . p ’ , " p i c k l e _ o u t p u t _ f i l e n a m e " : ’ msc−i m m u n i t y . p ’ , " pickle_input_filename " : cal , " r a w d a t a _ o u t p u t _ f i l e n a m e " : ’ o u t _ r a w _ i m m u n i t y−%s . d a t ’ , " p r o c e s s e d d a t a _ o u t p u t _ f i l e n a m e " : ’ o u t _ p r o c e s s e d _ i m m u n i t y−%s . d a t ’ , " l o g _ f i l e n a m e " : ’ msc . l o g ’ , " logger " : [ ’ stdlogger ’ ] , " m i n i m a l _ a u t o s a v e _ i n t e r v a l " : 3600 , " descriptions " : [ theboard ] , " measure_parameters " : [{ ’ d o t f i l e ’ : d o t f i l e , ’ c a l i b r a t i o n ’ : ’ empty ’ , ’ kernel ’ : ( kernel , kpars ) , ’ l e v e l i n g ’ : None , ’ freqs ’ : testfreqs , ’ names ’ : { ’ s g ’ : ’ s g ’ , ’ a1 ’ : ’ a1 ’ , ’ a2 ’ : ’ a2 ’ , ’ ant ’ : ’ ant ’ , ’ pmfwd ’ : ’pm1 ’ , ’pmbwd ’ : ’pm2 ’ , ’ fp ’ : [ ] , ’ tuner ’ : [ ’ tuner ’ ] , # take care : duty i s in %

29

3 Messungen zur Untersuchung der Störfestigkeit

54 55 56 57 58 59 60 61 62 } }] ,

’ refant ’ : [ ’ refant ’ ] , ’ pmref ’ : [ ’ pmref ’ ] } " e v a l u a t i o n _ p a r a m e t e r s " : [ { ’ e m p t y _ c a l ’ : " empty " , ’ loaded_cal ’ : " loaded " , ’ EUT_cal ’ : t h e b o a r d }]

Zunächst werden einige zusätzliche notwendige Module geladen. Das Modul os ist ein von Python zur Verfügung gestelltes Modul zur Zusammenarbeit mit dem Betriebssystem. Das Modul umdutil enthält nützliche Tools für die Messroutinen und Auswertung und wird vom Entwicklerteam der Universität Magdeburg bereitgestellt und betreut, daher auch der Name uni md utillities. Mit Hilfe des Moduls scipy (Scientiﬁc Tools for Python) kann man Python sehr gut für numerische Rechnungen einsetzen. Das Modul ImmunityThreshold schließlich enthält den eigentlichen Mess-Kernel und muss vom Anwender entsprechend der gewünschten Messung zur Verfügung gestellt werden. In Zeile 6 wird eine Umgebungsvariable abgefragt und der Variable umdpath zugeordnet. Diese Umgebungvarable muss unter dem Namen UMDPATH auf dem benutzten Arbeitsplatzrechner eingerichtet werden und enthält alle Pfade, in denen das Messprogramm nach benötigten Dateien suchern soll, wenn sich selbige nicht im Messordner beﬁnden oder mit Verweis auf den vollständigen Pfad übergeben werden. Eine dieser Dateien wäre zum Beispiel die .dot-Datei. Da bei der durchgeführten Messreihe immer wieder der selbe Messaufbau benutzt wurde, wurde die .dot-Datei aus Kapazitätsgründen nicht in jeden Ordner koipiert, sondern in einem Sammelordner für .dot-Dateien, dessen Pfad ebenfalls in der Umgebungsvariable UMDPATH enthalten sein muss. In Zeile 7 sucht dann der Befehl umdutil.GetFileFromPath () aus dem Modul umdutil nach dem übergebenen Namen der .dot-Datei (smallMSC-immunity-no-fp.dot). Diese Suche erfolgt erst im eigenen Messordner. Falls die Datei dort nicht gefunden wird, werden die Pfade, die in UMDPATH abgelegt sind, der Reihenfolge nach durchsucht, daher wird ebenfalls die Variable umdpath beim Befehlsaufruf übergeben. Alternativ kann der Name der benötigten .dot-Datei auch direkt der Variablen umdpath zugewiesen werden. Wenn sie in einem anderen Ordner als dem Messordner liegt, ist dazu natürlich die Angabe mit Pfad nötig. In Zeile 8 erfolgt Befehl, zur Kontrolle noch einmal auszugeben, welche dot-Datei nun für die Messung verwendet wird. In Zeile 10 und 12 erfolgt die Deﬁnition, bei welchen Frequenzen und Feldstärken die Messungen durchgeführt werden sollen. In diesem Fall soll also der Frequenzbereich von 3,3 GHz bis 3,85 GHz in Schritten von 50 MHz durchfahren werden und die Feldstärke jeweils in 10 V/mSchritten von 100 V/m bis 1000 V/m erhöht werden. Wird die Kammer im tuned mode betrieben, könnte hier auch deﬁniert werden, bei welchen Tunerpositionen gemessen werden soll. Da

30

3 Messungen zur Untersuchung der Störfestigkeit in diesem Beispiel die Messung im stirred mode erfolgte, ist das hier jedoch nicht nötig. In Zeile 14 wirde deﬁniert, welcher Kernel für die Messung genutzt werden soll. Anschließend erfolgt die Angabe der Parameter für den Kernel. Zeile 15 ist auskommentiert und spielt daher keine Rolle, die Parameter werden ab Zeile 16 übergeben. • tp bezeichnet die Tunerpositionen, bei denen gemessen werden soll. Hier würde die im vohergehenden Schritt deﬁnierte Liste oder das dictionary mit den Tunerpositionen übergeben werden. Wird nichts übergeben, werden die Tunerpositionen benutzt, die auch während der Kalibrierung Verwendung fanden. Wird ein None übergeben, wird davon ausgegangen, dass die Messung im stirred mode erfolgt, der Tuner wird vom Messprogramm nicht angesprochen und muss eigenhändig in Bewegung gebracht werden. • ﬁeld erhält die Liste der Testfeldstärken. • testfreqs bekommt die Liste der zu untersuchenden Frequenzen. • dwell bezeichnet die Zeit, die der Prüﬂing jeweils bei entsprechender Tunerposition und Frequenz der Testfeldstärke ausgesetzt ist. Hierbei ist es wichtig, das Zeitverhalten des Prüﬂing einschätzen zu können. Sollten die Messungen im stirred mode durchgeführt werden, sollte dwell mindest der Zeit für einen Tunerumlauf entsprechen. • what enthält hier die Parameter für die Prüﬂingsüberwachung. Da in diesem Beispiel das Rechtecksignal auf Pulsdauer, High-Pegel und Low-Pegel überwacht wurde, werden hier jeweils die Minimalwerte und Maximalwerte der Parameter übergeben, also das Wertefenster, innerhalb dessen das Signal noch als gültiges Signal gewertet wird, der Prüﬂing also fehlerfrei arbeitet. • PMfreq gibt die Pulswiederholrate an, da in diesem Beispiel der Prüﬂing mit pulsmodulierten Signalen beaufschlagt wurde. • PMduty bezeichnet das Tastverhältnis der Pulsmodulation in Prozent. Danach wird der aktuell benutze Kernel inklusive seiner Parameter noch einmal zur Kontrolle ausgegeben. Anschließend folgen noch eine Datei und Namenszuweisungen. Da der Kernel intern bestimmte Variablennamen verwendet, die nicht mit den übergebenen oder auszugebenen Varialblen oder Dateien übereinstimmen muss, ist es notwendig diese vorher noch anzugeben. Abschließend wird noch ein Konﬁgurationsblockcdict erzeugt, dass alle festgelegten Parameter, Dateien und

31

3 Messungen zur Untersuchung der Störfestigkeit Namen enthält und dann vom aufrufenden Messprogramm ausgewertet bzw. der Instanz der MSC-Klasse übergeben wird. Hierbei beﬁnden sich jeweils an erster Stelle die Namen, die von der Software intern benutzt werden, gefolgt von den Bezeichnungen, die der Anwender wünscht oder bereits verwendet hat. Die Punkte bedeuten im Einzelnen: • autosave_ﬁlename ist der Name der Autosave-Datei. • pickle_output_ﬁlename ist der Name der auszugebenen pickle-Datei. • pickle_input_ﬁlename ist der Name einer schon vorhandenen pickle-Datei, die vor Beginn der Messungen eingelesen werden soll. • rawdata_output_ﬁlename ist der Name der Ausgabedatei für die unbehandelten Messdaten. • processeddata_output_ﬁlename ist Name der Ausgabedatei für die Ergebnisdaten. • log_logﬁlename ist der Name der Datei, die alle Vorgänge während der Messung mitprotokolliert. • logger legt die Routine zum Führen der Protokolldatei fest. • minimal_autosave_interval ist die minimale Zeitspanne für die Autosaves in Sekunden, im Beispiel also eine Stunde. • description ist die Bezeichnung für die aktuelle Messung. Anschließend erfolgt die Übergabe der Messparameter für die Instanz der MSC-Klasse. Dabei werden folgende Werte übergeben: • dotﬁle ist der Name der, den Aufbau charakterisierenden, dot-Datei, welche weiter oben bereits deﬁniert wurde. • calibration bezeichnet den Namen der Kalibrierung, dessen Werte bei der Rechnung verwendet werden sollen. • kernel verweist auf den zu benutzenden Kernel samt seiner Parameter, die weiter oben deﬁniert wurden. • freqs sind die zu untersuchenden Frequenzen, die auch als Kernelparameter schon über-

32

3 Messungen zur Untersuchung der Störfestigkeit geben wurden. • names sind die Bezeichnungen der Elemente der Messkette. Hierbei sind die Namen, die der Anwender für die Elemente in der dot-Datei benutzt, zu übergeben. Letztlich werden noch die Namen angegeben, unter denen die Kalibrierungen im pickle-ﬁle abgelegt sind. Diese Informationen werden von der Auswerteroutine benötigt.

3.3 Messung
Zum Start der Messung muss man sich im Konsolenmodus beﬁnden. Dazu ruft man über Start Ausführen... die Eingabeaufforderung auf und gibt das Kommando cmd <ENTER> ein. Anschließend wechselt man in der sich öffnenden Konsole in das Verzeichnis des aktuellen Messordners. dort ruft man zum Start in der Umgebung python das Messprogramm, gefolgt vom Konﬁgurationsﬁle, auf. Dies ist in Abbildung 3.5 zu sehen.

Abbildung 3.5: Aufruf des Messprogramms Die eigentliche Messung verläuft bei Störfestigkeitsmessungen nach einem etwas anderen Schema. Zunächst wird ebenfalls durch das aufrufende Messprogramm, hier msc-immunity.py, eine Instanz der Klasse MSC erzeugt. Dieser Instanz wird innerhalb der Messparameter measurement_parameters auch ein Verweis auf den zu benutzenden Messkernel sowie dessen Parameter übergeben. Anders als bei Kalibrier- und Emissionsmessungen in denen die MSC-Klasse die Informationen über den Ablauf der Messungen enthält, sind diese Informationen bei Störfestigkeitsmessungen in diesem Messkernel enthalten. Dieses ist aus Flexibilitätsgründen erforderlich, da sich bei Störfestigkeitsmessungen der Ablauf der Messungen häuﬁg ändern kann, beispielsweise könnte die Testfeldstärke langsam erhöht werden oder der Prüﬂing auch gleich mit einer Grenzfeldstärke beaufschlagt werden. Außerdem muss die EUT-Überwachung während

33

3 Messungen zur Untersuchung der Störfestigkeit der Messungen realisiert werden. Aus diesem Grund werden die Informationen über den Ablauf der Messung in einen Kernel ausgelagert, der dann entsprechend der gewünschten Messung vom Anwender zur Verfügung editiert werden muss. Die Instanz der MSC-Klasse erzeugt dann eine Instanz dieses Messkernels und übergibt dieser die Kernelparameter. Die Kernelinstanz bestimmt dann den Ablauf der Messung incl. EUT-Überwachung und leitet die MSC-Instanz somit bei der Durchführung der Messung an.

3.3.1 Der Messkernel ImmunityThreshholdTDS4.py
Der Aufbau des Messkernels ist im Listing 3.3 zu sehen. Listing 3.3: Messkernel ImmunityThresholdTDS4.py
1 2 3 4 5 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 import t i m e import u m d u t i l import u m d d e v i c e import p p r i n t import TDSClass c l a s s ImmunityKernel_Thres : def _ _ i n i t _ _ ( s e l f , messenger , UIHandler , locals , dwell , k e y l i s t = ’ sS ’ , t p =None , f i e l d =None , t e s t f r e q s =None , what =None , PMfreq=None , PMduty=None ) : self . field=field s e l f . mg= l o c a l s [ ’mg ’ ] names= l o c a l s [ ’ names ’ ] ddict=locals [ ’ ddict ’ ] s e l f . s g = d d i c t [ names [ ’ s g ’ ] ] self . testfreqs=testfreqs self . goto_next_freq=False i f s e l f . f i e l d i s None : s e l f . f i e l d =range (10 ,110 ,10) s e l f . tp=tp s e l f . what = what s e l f . messenger=messenger s e l f . UIHandler=UIHandler self . callerlocals=locals try : self . in_as= self . c a l l e r l o c a l s [ ’ in_as ’ ] except KeyError : s e l f . i n _ a s ={} s e l f . messenger ( p p r i n t . pformat ( s e l f . in_as ) , [ ] ) s e l f . _ t e s t p l a n = s e l f . _makeTestPlan ( ) s e l f . dwell = dwell self . keylist = keylist s e l f . history =[] i f PMfreq i s n o t None and PMduty i s n o t None : s e l f . s g . ConfPM ( 0 , PMfreq , 0 , 1 . 0 / PMfreq∗PMduty ∗ 0 . 0 1 , 0 ) s e l f . s g . PMOn ( ) s e l f . p a r p o r t = TDSClass . P a r P o r t ( on = 2 5 5 , off= 0 , p o r t = 0 x378 , i n i t s t a t = 0 x0 , d l l n a m e = ’m : \ \ d l l s \ \ i n p o u t 3 2 . d l l ’ ) s e l f . t d s = TDSClass . TDS420_EUT_Handler ( EUTdll = ’m : \ \ d l l s \ \ e u t−t d s 4 2 0−s i m p l e . d l l ’ ,

34

3 Messungen zur Untersuchung der Störfestigkeit

51

INIFILE = ’M: \ \ umd−c o n f i g \ \ smallMSC \ \ i n i \ \ e u t−t d s 4 2 0−s i m p l e . i n i ’ )

54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 105 106 107 108 109 111 112 113 114 116 117 118 120 122 123 124 125

def _makeTestPlan ( s e l f ) : ret = [] i f s e l f . t p i s None : for f in f r e q s : has_f = f in s e l f . i n _ a s . keys ( ) s e l f . m e s s e n g e r ( " f=%e i n i n _ a s . k e y s ( ) ? : %r " %( f , h a s _ f ) , [ ] ) i f has_f : continue r e t . a p p e n d ( ( ’ LoopMarker ’ , ’ ’ , { } ) ) r e t . append ( ( ’ r f ’ , ’ ’ , { ’ r f o n ’ : 0}) ) r e t . append ( ( ’ a u t o s a v e ’ , ’ ’ , {}) ) r e t . append ( ( ’ f r e q ’ , ’ ’ , { ’ f r e q ’ : f }) ) f o r _e i n s e l f . f i e l d : try : _e = u m d e v i c e . UMDMResult ( _e , u m d d e v i c e . UMD_Voverm ) except : pass r e t . a p p e n d ( ( ’ e f i e l d ’ , ’ ’ , { ’ e f i e l d ’ : _e } ) ) r e t . append ( ( ’ r f ’ , ’ ’ , { ’ r f o n ’ : 1}) ) r e t . append ( ( ’ measure ’ , ’ ’ , {}) ) r e t . a p p e n d ( ( ’ e u t ’ , None , None ) ) r e t . append ( ( ’ r f ’ , ’ ’ , { ’ r f o n ’ : 0}) ) r e t . append ( ( ’ f i n i s h e d ’ , ’ ’ , {}) ) e l s e : # tuned f r e q s = s e l f . tp . keys ( ) freqs . sort () for f in f r e q s : has_f = f in s e l f . i n _ a s . keys ( ) i f has_f : continue r e t . a p p e n d ( ( ’ LoopMarker ’ , ’ ’ , { } ) ) r e t . append ( ( ’ r f ’ , ’ ’ , { ’ r f o n ’ : 0}) ) r e t . append ( ( ’ a u t o s a v e ’ , ’ ’ , {}) ) r e t . append ( ( ’ f r e q ’ , ’ ’ , { ’ f r e q ’ : f }) ) f o r _e i n s e l f . f i e l d : try : _e = u m d e v i c e . UMDMResult ( _e , u m d d e v i c e . UMD_Voverm ) except : pass r e t . a p p e n d ( ( ’ e f i e l d ’ , ’ ’ , { ’ e f i e l d ’ : _e } ) ) for t in s e l f . tp [ f ] : r e t . append ( ( ’ t u n e r ’ , ’ ’ , { ’ t u n e r p o s ’ : t [ : ] } ) ) r e t . append ( ( ’ r f ’ , ’ ’ , { ’ r f o n ’ : 1}) ) r e t . append ( ( ’ measure ’ , ’ ’ , {}) ) r e t . a p p e n d ( ( ’ e u t ’ , None , None ) ) r e t . append ( ( ’ r f ’ , ’ ’ , { ’ r f o n ’ : 0}) ) r e t . append ( ( ’ f i n i s h e d ’ , ’ ’ , {}) ) ret . reverse () return r e t def t e s t ( s e l f , s t a t ) : i f s t a t == ’ A m p l i f i e r P r o t e c t i o n E r r o r ’ : s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " RFOff . . . " , [ ] ) s e l f . mg . R F O f f _ D e v i c e s ( ) s e l f . g o t o _ n e x t _ f r e q =True if self . goto_next_freq : cmd = s e l f . _ _ g o t o _ n e x t _ f r e q ( ) else : cmd = s e l f . _ t e s t p l a n . pop ( ) # o v e r r e a d LoopMarker w h i l e cmd [ 0 ] = = ’ LoopMarker ’ : cmd = s e l f . _ t e s t p l a n . pop ( ) s e l f . h i s t o r y . a p p e n d ( cmd ) i f cmd [ 0 ] == ’ e u t ’ : s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " S t a r t EUT c h e c k i n g . . . " , [ ] ) s t a t , d e t a i l = s e l f . t d s . TestEUT ( s e l f . what , s e l f . d w e l l ) d e t a i l [ ’ O K _ a f t e r _ i n t e r n a l _ r e s e t ’ ] = None # stirred freqs = self . testfreqs [:]

35

3 Messungen zur Untersuchung der Störfestigkeit

126 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144 145 146 147 148 149 150 151 153 154 155 156 157 158 159 160 161 162 163 164 165 166 167 168 169 170 171 172 174 175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 191 192 193 194 195 196 197

d e t a i l [ ’ O K _ a f t e r _ e x t e r n a l _ r e s e t ’ ] = None d e t a i l [ ’ O K _ a f t e r _ u s e r _ r e s e t ’ ] = None i f not s t a t : s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " S t a r t EUT c h e c k i n g a g a i n . . . " , [ ] ) s t a t , d e t a i l = s e l f . t d s . TestEUT ( s e l f . what , s e l f . d w e l l ) d e t a i l [ ’ O K _ a f t e r _ i n t e r n a l _ r e s e t ’ ] = None d e t a i l [ ’ O K _ a f t e r _ e x t e r n a l _ r e s e t ’ ] = None d e t a i l [ ’ O K _ a f t e r _ u s e r _ r e s e t ’ ] = None i f not s t a t : s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " S t a r t EUT c h e c k i n g a g a i n . . . " , [ ] ) s t a t , d e t a i l = s e l f . t d s . TestEUT ( s e l f . what , s e l f . d w e l l ) d e t a i l [ ’ O K _ a f t e r _ i n t e r n a l _ r e s e t ’ ] = None d e t a i l [ ’ O K _ a f t e r _ e x t e r n a l _ r e s e t ’ ] = None d e t a i l [ ’ O K _ a f t e r _ u s e r _ r e s e t ’ ] = None i f not s t a t : s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " S t a r t EUT c h e c k i n g a g a i n . . . " , [ ] ) s t a t , d e t a i l = s e l f . t d s . TestEUT ( s e l f . what , s e l f . d w e l l ) d e t a i l [ ’ O K _ a f t e r _ i n t e r n a l _ r e s e t ’ ] = None d e t a i l [ ’ O K _ a f t e r _ e x t e r n a l _ r e s e t ’ ] = None d e t a i l [ ’ O K _ a f t e r _ u s e r _ r e s e t ’ ] = None i f not s t a t : s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " S t a r t EUT c h e c k i n g a g a i n . . . " , [ ] ) s t a t , d e t a i l = s e l f . t d s . TestEUT ( s e l f . what , s e l f . d w e l l ) d e t a i l [ ’ O K _ a f t e r _ i n t e r n a l _ r e s e t ’ ] = None d e t a i l [ ’ O K _ a f t e r _ e x t e r n a l _ r e s e t ’ ] = None d e t a i l [ ’ O K _ a f t e r _ u s e r _ r e s e t ’ ] = None i f not s t a t : remeasure=False s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " TestEUT r e t u r n s s t a t =%r , d e t a i l =%r " %( s t a t , d e t a i l ) , [ ] ) s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " RFOff " , [ ] ) s e l f . mg . R F O f f _ D e v i c e s ( ) s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " Going t o s l e e p f o r 25 s e c o n d s . . . " , [ ] ) time . sleep (25) s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " . . . b a c k . Check EUT a g a i n . . . " , [ ] ) s t a t 2 , d e t a i l 2 = s e l f . t d s . TestEUT ( s e l f . what , 1 ) s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " TestEUT r e t u r n s s t a t =%r , d e t a i l =%r " %( s t a t 2 , d e t a i l 2 ) , [ ] ) detail [ ’ OK_after_internal_reset ’ ] = stat2 i f n o t s t a t 2 : # s t i l l n o t ok s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " Doing h a r d r e s e t . . . " , [ ] ) s e l f . p a r p o r t . doReset ( ) s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " Going t o s l e e p f o r 25 s e c o n d s . . . " , [ ] ) time . sleep (25) s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " . . . b a c k . Check EUT a g a i n . . . " , [ ] ) s t a t 2 , d e t a i l 2 = s e l f . t d s . TestEUT ( s e l f . what , 1 ) s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " TestEUT r e t u r n s s t a t =%r , d e t a i l =%r " %( s t a t 2 , d e t a i l 2 ) , []) detail [ ’ OK_after_external_reset ’ ] = stat2 while not s t a t 2 : # g i v e up and w a i t f o r u s e r

msg = " U n a b l e t o r e c o v e r EUT s t a t u s a f t e r e x t e r n a l r e s e t . \ n \ n C o n t i n u e : C o n t i n u e m e a s u r e m e n t a f t e r EUT r e s e t by u s e r . \ n Q u i t : Q u i t m e a s u r e m e n t . " but = [ " Continue " , " Quit " ] a n s w e r = s e l f . m e s s e n g e r ( msg , b u t ) i f a n s w e r == b u t . i n d e x ( ’ Q u i t ’ ) : s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " m e a s u r e m e n t t e r m i n a t e d by u s e r . " , [ ] ) r a i s e UserWarning # to reach f i n a l l y s t a t e m e n t e l i f a n s w e r == b u t . i n d e x ( ’ C o n t i n u e ’ ) : msg2 = " Measure t h i s f r e q u e n c y a g a i n ? \ n \ nYes : Measure a g a i n \ nNo : C o n t i n u e w i t h next frequency . " b u t 2 = [ " Yes " , "No" ] a n s w e r 2 = s e l f . m e s s e n g e r ( msg2 , b u t 2 ) i f a n s w e r 2 == b u t 2 . i n d e x ( ’ Yes ’ ) : remeasure =True else : remeasure=False comment = r a w _ i n p u t ( ’ Comment : ’ ) d e t a i l [ ’ comment ’ ] = comment s t a t 2 , d e t a i l 2 = s e l f . t d s . TestEUT ( s e l f . what , 1 ) detail [ ’ OK_after_user_reset ’ ] = stat2 i f remeasure : self . history . reverse () s e l f . _ t e s t p l a n . extend ( s e l f . h i s t o r y ) cmd = ( None , " " , { } )

36

3 Messungen zur Untersuchung der Störfestigkeit

198 199 200 201 202 203 204 205 206 207 208 209 210 211 212 214 215 216 217 218 219 220 221 else : else : else : else :

else : cmd = ( ’ e u t ’ , ’ s t a t ! = 0 ’ , { ’ e u t s t a t u s ’ : d e t a i l . copy ( ) } ) s e l f . g o t o _ n e x t _ f r e q =True else : cmd = ( ’ e u t ’ , ’ ’ , { ’ e u t s t a t u s ’ : ’OK’ } ) cmd = ( ’ e u t ’ , ’ ’ , { ’ e u t s t a t u s ’ : ’OK’ } ) cmd = ( ’ e u t ’ , ’ ’ , { ’ e u t s t a t u s ’ : ’OK’ } ) cmd = ( ’ e u t ’ , ’ ’ , { ’ e u t s t a t u s ’ : ’OK’ } ) cmd = ( ’ e u t ’ , ’ ’ , { ’ e u t s t a t u s ’ : ’OK’ } ) s e l f . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " . . . EUT c h e c k i n g done . " , [ ] ) r e t u r n cmd def __goto_next_freq ( s e l f ) : self . goto_next_freq=False s e l f . history =[] while True : cmd = s e l f . _ t e s t p l a n . pop ( ) i f cmd [ 0 ] i n ( ’ LoopMarker ’ , ’ f i n i s h e d ’ ) : break r e t u r n cmd

Zunächst werden wieder einige Module geladen, das Modul TDSClass regelt die Kommunikation mit dem Oszilloskop TDS 420, mit dem die Überwachung des Ausgangsimpulses des PC-Boards erfolgte. Anschließend wird die Klasse ImmunityKernel_Thres mit einigen Parametern erzeugt und einige Variablen festgelegt. Hier ﬁnden sich unter anderem die Parameter wieder, die in der Konﬁgurationsdatei festgelegt wurden. In Zeile 45 und 50 werden Instanzen der Klassen ParPort und TDS420_EUT_Handler aus dem Modul TDSClass erzeugt, die für die Resetauslösung beim EUT sowie für die Überwachung des selbigen verantwortlich sind. Anschließend wird der Messablauf festgelegt, also die Schleifen, in denen Tunerpositionen, Frequenzen und Feldstärken während der Messung verändert werden. Im Beispielkernel liegt die Frequenzschleife außen und die Tunerschleife ganz innen, es wird also zunächst eine Frequenz eingestellt, dann ein Feldstärkelevel gewählt und anschließend der Tuner im stirred oder tuned mode eine Umdrehung bewegt. Sollte kein EUT-Ausfall detektiert worden sein, wird das Feldstärkelevel erhöht und wieder der Tuner gedreht. Dies erfolgt so lange, bis ein Ausfall des EUT detektiert wurde oder der Prüﬂing mit der maximalen zu untersuchenden Feldstärke beaufschlagt wurde. Dann wird die nächste Frequenz angefahren und die Untersuchung weitergeführt. Die Wahl, in welcher Schleife welche Größe geändert wird, liegt beim Anwender, wobei die Bestrebungen dahin gehen sollten, die Messung möglichst effektiv zu gestalten. Achtung: Im stirred mode der MVK, also bei den Messungen mit durchlaufendem Tuner, wird der Tuner nicht über die Software gesteuert, sondern muss vom Anwender in Bewegung gebracht werden. Eine weitere erforderliche Routine ist die Funktion test. Hier wird die Funktion des EUT überprüft. Es werden, wie beschrieben, die Ein- und Ausschaltlevel sowie die Periodendauer des vom PC-Board ausgegebenen Signals überprüft. Die jeweilige Ober- und Untergrenzen der

37

3 Messungen zur Untersuchung der Störfestigkeit entsprechenden Werte werden der Funktion TestEUT übergeben und von dieser mit den vom Oszilloskop ausgebenen Werten verglichen. Diese Überprüfung der Oszilloskopdaten erfolgt bis zu fünf mal hintereinander, daher auch die Verschachtelung im Quellcode. Die mehrfache Überprüfung machte sich erforderlich, da das vom EUT erhaltene Signal nicht immer sauber erfasst wurde und dadurch angebliche EUT-Ausfälle gemeldet wurden, die nicht stattfanden. Wenn nach der fünften Überprüfung immer noch nicht das richtige Signal detektiert wird (Zeile 153) wartete die Testroutine 25 Sekunden auf ein evtl. selbstständiges Reset des EUT (Zeile 159). Wurde nach Ablauf der Zeitspanne das Signal immer noch nicht detektiert, wird in Zeile 166 mit Hilfe der Funtion doReset ein externes Reset des PCBoards über den Parallelport des Messrechners ausgelöst und abermals 25 Sekunden gewartet. Ist das Signal des EUT dann immer noch nicht da, hält das Programm mit einer Meldung an den Anwender an und wartet auf weitere Befehle(Zeile 175). Nach Überprüfung oder Instandsetzung des EUT kann die Messung mit Continue fortgesetzt werden. Wird nun oder auch schon während der vorherigen Prüfung festgestellt, das das EUT ein korrektes Ausgangssignal liefert, wird die Messung normal fortgesetzt. Es benötigt also etwas Zeit und Aufwand, um die automatische EUT-Überwachung ins Messprogramm zu integrieren, dafür vereinfacht es natürlich später den eigentlichen Messablauf erheblich. Es ist offensichtlich, dass bei gewünschten Änderungen im Messablauf oder bei der Überwachung anderer EUT die Kerneldatei editiert, also geändert werden muss. Anschließend muss sie, möglichst unter einem anderen aussagekräftigen Namen, im Messordner oder unter einem der in der Umgebungsvariable UMDPATH, die weiter oben beschrieben wurde, angegebenen Pfade, gespeichert werden. Die Zuweisung des aktuellen Messkernels erfolgt dann, wie beschrieben in der Konﬁgurationsdatei 3.2 in Zeile 4.

3.3.2 Das Messprogramm msc-immunity.py
Die im Messordner enthaltene Datei msc-immunity.py ist das eigentliche Messprogramm. Sie ist im Listing 3.4 zu sehen. Diese Datei muss in der Regel nicht geändert werden, da Veränderungen am Messaufbau oder der Messparameter, wie z.B. der zu untersuchende Frequenzbereich durch Änderungen in der dot-Datei bzw. in der Konﬁgurationsdatei dem Messprogramm mitgeteilt werden. Listing 3.4: msc-immunity.py
1 2 3 4 5 6 7 8 import o s import s y s import g z i p import p p r i n t try : import c P i c k l e a s p i c k l e except ImportError : import p i c k l e

38

3 Messungen zur Untersuchung der Störfestigkeit

9 10 11

import MSC import u m d d e v i c e import u m d u t i l

14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 46 47 48 49 50 52 53 54 55 56 57 58 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 77 78 79 80 81 82 83

c d i c t = { " a u t o s a v e _ f i l e n a m e " : ’ msc−a u t o s a v e . p ’ , " p i c k l e _ o u t p u t _ f i l e n a m e " : ’ msc−i m m u n i t y . p ’ , " p i c k l e _ i n p u t _ f i l e n a m e " : None , " r a w d a t a _ o u t p u t _ f i l e n a m e " : ’ o u t _ r a w _ i m m u n i t y−%s . d a t ’ , " p r o c e s s e d d a t a _ o u t p u t _ f i l e n a m e " : ’ o u t _ p r o c e s s e d _ i m m u n i t y−%s . d a t ’ , " l o g _ f i l e n a m e " : ’ msc . l o g ’ , " logger " : [ ’ stdlogger ’ ] , " m i n i m a l _ a u t o s a v e _ i n t e r v a l " : 3600 , " d e s c r i p t i o n s " : [ ’EUT ’ ] , " m e a s u r e _ p a r a m e t e r s " : [ { ’ d o t f i l e ’ : ’ smallMSC−i m m u n i t y . d o t ’ , ’ c a l i b r a t i o n ’ : ’ empty ’ , ’ k e r n e l ’ : ( None , { } ) , ’ l e v e l i n g ’ : None , ’ f r e q s ’ : None , ’ names ’ : { ’ s g ’ : ’ s g ’ , ’ a1 ’ : ’ a1 ’ , ’ a2 ’ : ’ a2 ’ , ’ ant ’ : ’ ant ’ , ’ pmfwd ’ : ’pm1 ’ , ’pmbwd ’ : ’pm2 ’ , ’ fp ’ : [ ] , ’ tuner ’ : [ ’ tuner1 ’ ] , ’ refant ’ : [ ’ refant1 ’ ] , ’ pmref ’ : [ ’ pmref1 ’ ] } }] , " e v a l u a t i o n _ p a r a m e t e r s " : [ { ’ e m p t y _ c a l ’ : " empty " , ’ loaded_cal ’ : " loaded " , ’ EUT_cal ’ : ’EUT ’ }] } d e f myopen ( name , mode ) : i f name [ −3:] == ’ . gz ’ : r e t u r n g z i p . open ( name , mode ) else : r e t u r n f i l e ( name , mode ) def update_conf ( c d i c t ) : try : import c o n f i g c d i c t . update ( config . c d i c t ) p r i n t " C o n f i g u r a t i o n u p d a t e d from ’ c o n f i g . py ’ . " except ImportError : pass i f l e n ( s y s . a r g v ) >1: f o r name i n s y s . a r g v [ 1 : ] : try : d , nm = o s . p a t h . s p l i t ( name ) _mod = _ _ i m p o r t _ _ ( nm [ : nm . r i n d e x ( ’ . ’ ) ] ) c d i c t . u p d a t e ( g e t a t t r ( _mod , ’ c d i c t ’ ) ) p r i n t " C o n f i g u r a t i o n u p d a t e d from ’% s ’ . "%name except : raise try : d c t = e v a l ( name ) i f t y p e ( d c t ) == t y p e ( { } ) : c d i c t . update ( dct ) p r i n t " C o n f i g u r a t i o n u p d a t e d from ’% s ’ . "%s t r ( d c t ) except : pass d e f l o a d _ f r o m _ a u t o s a v e ( fname ) : msc=None cmd=None i f o s . p a t h . i s f i l e ( fname ) : try : p f i l e = myopen ( fname , " r b " ) msc= p i c k l e . l o a d ( p f i l e )

39

3 Messungen zur Untersuchung der Störfestigkeit

84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 109 110 111 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127 128 129 130

cmd=msc . ascmd i f msc : msg = " A u t o s a v e i l e %s f o u n d . \ ncmd : %s \ n \ nResume : Resume Measurement \ nNew : S t a r t new . " %(fname , cmd ) b u t = [ " Resume " , "New" ] a n s w e r = msc . m e s s e n g e r ( msg , b u t ) # a n s w e r =0 i f a n s w e r == b u t . i n d e x ( ’ Resume ’ ) : startnew = False else : d e l msc d e l cmd msc=None cmd=None e x c e p t I O E r r o r , m: # t h i s i s no p r o b l e m msc . m e s s e n g e r ( " I O E r r o r d u r i n g c h e c k f o r a u t o s a v e−f i l e : %s \ n C o n t i n u e w i t h n o r m a l o p e r a t i o n . . . "%m, [ ] ) e x c e p t ( U n p i c k l i n g E r r o r , A t t r i b u t e E r r o r , EOFError , I m p o r t E r r o r , I n d e x E r r o r ) , m: # u n p i c k l e was n o t s u c c e s f u l , b u t we w i l l c o n t i n u e anyway # u s e r can d e c i d e l a t e r except : # r a i s e a l l unhadled e x c e p t i o n s raise r e t u r n msc , cmd d e f m a k e _ l o g g e r _ l i s t ( msc , c l o g g e r ) : logger = [] for _l in clogger : _ l s t = _l . s p l i t ( ’ . ’ ) _mod=None i f l e n ( _ l s t ) ==1: # no module g i v e n _mod = msc e l i f l e n ( _ l s t ) ==2: try : _mod = _ _ i m p o r t _ _ ( _ l s t [ 0 ] ) e x c e p t I m p o r t E r r o r , m: _mod = None msc . m e s s e n g e r ( " I m p o r t E r r o r : %s "%m, [ ] ) i f _mod : try : l o g g e r . a p p e n d ( g e t a t t r ( msc , _ l ) ) e x c e p t A t t r i b u t e E r r o r , m: msc . m e s s e n g e r ( " L o g g e r n o t f o u n d : %s "%m, [ ] ) i f not l e n ( l o g g e r ) : return logger [ : ] # empty l o g g e r = [ msc . s t d l o g g e r ] # f a l l b a c k t o s t d l o g g e r # _ l s t can be e . g . [ s t d l o g g e r ] o r [ custom , F i l e t a b l o g g e r ] i f he want t o f i n i s h . msc . m e s s e n g e r ( " E r r o r d u r i n g u n p i c k l e o f a u t o s a v e−f i l e : %s \ n C o n t i n u e w i t h n o r m a l o p e r a t i o n . . . "%m, [ ] )

133 135 136 137 138 140 142 143 144 145 146 147 148 149 150 151 152 153 154 155 157 158

i f __name__ == ’ __main__ ’ : update_conf ( cdict ) print " Configuration values : " print pprint . pprint ( cdict ) msc , cmd= l o a d _ f r o m _ a u t o s a v e ( c d i c t [ ’ a u t o s a v e _ f i l e n a m e ’ ] ) i f n o t msc : if cdict [ ’ pickle_input_filename ’ ]: p f i l e = myopen ( c d i c t [ ’ p i c k l e _ i n p u t _ f i l e n a m e ’ ] , " r b " ) p r i n t " L o a d i n g i n p u t p i c k l e f i l e ’% s ’ . . . "%c d i c t [ ’ p i c k l e _ i n p u t _ f i l e n a m e ’ ] msc= p i c k l e . l o a d ( p f i l e ) pfile . close () p r i n t " . . . done " else : msc=MSC.MSC ( ) msc . s e t L o g F i l e ( c d i c t [ ’ l o g _ f i l e n a m e ’ ] ) l o g g e r = m a k e _ l o g g e r _ l i s t ( msc , c d i c t [ ’ l o g g e r ’ ] ) msc . s e t L o g g e r ( l o g g e r ) msc . s e t A u t o S a v e ( c d i c t [ ’ a u t o s a v e _ f i l e n a m e ’ ] ) msc . S e t A u t o S a v e I n t e r v a l ( c d i c t [ ’ m i n i m a l _ a u t o s a v e _ i n t e r v a l ’ ] ) descriptions = cdict [ ’ descriptions ’ ][:] for _i , _des in enumerate ( c d i c t [ ’ d e s c r i p t i o n s ’ ] ) :

40

3 Messungen zur Untersuchung der Störfestigkeit

159 160 161 162 163 164 165 166 167 168 169 170 171 172 173 174 175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190 191 192 193 194 195 196 197 198 199 200 201 202 203 204 205 206 207 208 209 210 211 212 213 214 215 216 218 219 220 221 222 223 224 225 226 227 228 229 230 231 232 try : else : try : else :

try : mp = c d i c t [ ’ m e a s u r e _ p a r a m e t e r s ’ ] [ _ i ] except IndexError : mp = c d i c t [ ’ m e a s u r e _ p a r a m e t e r s ’ ] [ 0 ] mp [ ’ d e s c r i p t i o n ’ ] = _ d e s try : ep = c d i c t [ ’ e v a l u a t i o n _ p a r a m e t e r s ’ ] [ _ i ] except IndexError : ep = c d i c t [ ’ e v a l u a t i o n _ p a r a m e t e r s ’ ] [ 0 ] ep [ ’ d e s c r i p t i o n ’ ] = _ d e s domeas= T r u e d o e v a l =True i f msc . r a w D a t a _ I m m u n i t y . h a s _ k e y ( _ d e s ) : domeas= F a l s e doeval=False msg = " " " " Measurement w i t h d e s c r i p t i o n ’%s ’ a l l r e a d y f o u n d i n MSC i n s t a n c e . \ n How do you want t o p r o c e e d ? \ n \ n C o n t i n u e : C o n t i n u e w i t h Measurement . \ n S k i p : S k i p Measurement b u t do E v a l u a t i o n . \ n B r e a k : S k i p Measurement and E v a l u a t i o n . \ n Exit : Exit Application " " " %( _ d e s ) but = [ " Continue " , " Skip " , " Break " , " E x i t " ] a n s w e r = msc . m e s s e n g e r ( msg , b u t ) # a n s w e r =0 i f a n s w e r == b u t . i n d e x ( ’ B r e a k ’ ) : continue e l i f a n s w e r == b u t . i n d e x ( ’ E x i t ’ ) : sys . e x i t ( ) e l i f a n s w e r == b u t . i n d e x ( ’ C o n t i n u e ’ ) : domeas= T r u e d o e v a l =True e l i f a n s w e r == b u t . i n d e x ( ’ S k i p ’ ) : domeas= F a l s e d o e v a l =True else : # be s a v e and do n o t h i n g continue i f domeas : msc . M e a s u r e _ I m m u n i t y (∗∗mp ) i f doeval : msc . OutputRawData_Immunity ( fname = c d i c t [ " r a w d a t a _ o u t p u t _ f i l e n a m e " ]% _ d e s ) msc . E v a l u a t e _ I m m u n i t y (∗∗ ep ) msc . O u t p u t P r o c e s s e d D a t a _ I m m u n i t y ( fname = c d i c t [ " p r o c e s s e d d a t a _ o u t p u t _ f i l e n a m e " ]%( " _ " . j o i n ( d e s c r i p t i o n s ) ) ) msg= " S e l e c t d e s c r i p t i o n t o u s e . \ n " but = [ ] f o r _i , _des i n enumerate ( c d i c t [ ’ d e s c r i p t i o n s ’ ] ) : msg+=’%d : %s ’%( _ i , _ d e s ) b u t . a p p e n d ( ’% d : %s ’%( _ i , _ d e s ) ) a n s w e r =msc . m e s s e n g e r ( msg , b u t ) mp = c d i c t [ ’ m e a s u r e _ p a r a m e t e r s ’ ] [ a n s w e r ] except IndexError : mp = c d i c t [ ’ m e a s u r e _ p a r a m e t e r s ’ ] [ 0 ] mp [ ’ d e s c r i p t i o n ’ ] = c d i c t [ ’ d e s c r i p t i o n s ’ ] [ a n s w e r ] e x e c ( cmd ) i f os . pa th . i s f i l e ( c d i c t [ ’ p i c k l e _ o u t p u t _ f i l e n a m e ’ ] ) : msg = " P i c k l e f i l e %s a l l r e a d y e x i s t . \ n \ n O v e r w r i t e : O v e r w r i t e f i l e \ nAppend : Append t o f i l e . " %( c d i c t [ ’ pickle_output_filename ’]) b u t = [ " O v e r w r i t e " , " Append " ] a n s w e r = msc . m e s s e n g e r ( msg , b u t ) i f a n s w e r == b u t . i n d e x ( ’ O v e r w r i t e ’ ) : mode = ’wb ’ else : mode = ’ ab ’ mode = ’wb ’ msc . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " p i c k l e r e s u l t s t o ’%s ’ . . . " %( c d i c t [ ’ p i c k l e _ o u t p u t _ f i l e n a m e ’ ] ) , [ ] ) p f = myopen ( c d i c t [ ’ p i c k l e _ o u t p u t _ f i l e n a m e ’ ] , mode ) p i c k l e . dump ( msc , pf , 2 ) msc . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " . . . done . " , [ ] )

41

3 Messungen zur Untersuchung der Störfestigkeit

233 234 235 236 237 238 239 240 241

except : msc . m e s s e n g e r ( u m d u t i l . t s t a m p ( ) + " f a i l e d t o p i c k l e t o %s " %( c d i c t [ ’ p i c k l e _ o u t p u t _ f i l e n a m e ’ ] ) , [ ] ) raise else : # remove a u t o s a v e f i l e try : o s . remove ( c d i c t [ ’ a u t o s a v e _ f i l e n a m e ’ ] ) except : pass a f t e r m e a s u r e m e n t i s c o m p l e t e d and c l a s s i n s t a n c e was p i c k l e d

Zunächst werden wieder einige Module und plug-ins importiert. pickle ist zur Erzeugung der pickle-Dateien erforderlich. MSC und umddevice sind an der Universität Magdeburg programmierte Module zur Durchführung der einzelnen Messroutinen bzw. zur Kommunikation mit den Messgeräten. Danach erfolgt die Vorbelegung der Variablen des dictionaries mit defaultWerten. Diese werden dann später ggf. beim Einladen des Konﬁgurationsﬁles aktualisiert. Anschließend werden einige Routinen deﬁniert. Die Routine myopen liefert bei Aufruf die in der Variable name geforderte Datei zurück, sollte sie gepackt sein, wird sie vorher noch entpackt. Durch update_conf wird ein Update des Koﬁgurationsdictionaries durchgeführt, die bisherigen Einträge in dict also gegebenfalls durch neue Einträge ersetzt, die, in Abhängigkeit von der aufrufenden Routine, aus einer Autosavedatei, einer geladen pickle-Datei oder auch aus der mit dem Messprogramm aufgerufenen Konﬁgurationsdatei stammen können. Durch die Routine load_from_autosave wird eine Autosavedatei geladen. make_logger_list stellt eine Liste von für Protokolldateien zuständigen Routinen zur Verfügung. Dann beginnt in Zeile 133 das eigentliche Programm. In Zeile 133 beginnt dann das eigentliche Programm. Zunächst wird ein Update der Messvariablen durchgeführt und diese dann anschließend ausgegeben. Dann versucht das Messprogramm, eine Instanz der Klasse MSC zu erstellen. Hierzu wird zunächst mit Hilfe der Routine load_from_autosave überprüft, ob bereits eine Autosavedatei unter dem im Koﬁgurationsblockcdict angegebenen Namen existiert. Gibt es diese Autosavedatei, wird abgefragt, ob sie eingelesen werden soll und bei Bestätigung in Zeile 140 nach dem Einlesen der Daten der Autosavedatei die gespeicherte Instanz der Klasse MSC wieder erstellt. Der zweite zurückgelieferte Wert cmd liefert das Kommando zurück, das die Routine aufrief, in der die Autosavedatei erstellt wurde, also die Routine, die bei Speicherung der Daten gerade lief. Anschließend wird in Zeile 204 abgefragt, welche der unter verschiedenen Descriptions abgespeicherten Messungen man verwenden möchte. Anschließend werden die aktuellen Messparameter mp übergeben und in Zeile 216 die gespeicherte begonnene Messung mit dem erneuten Aufruf der in cmd gespeicherten letzten aufgerufenen Routine an der gesicherten Stelle weitergeführt. Gibt es keine Autosavedatei unter dem angegebenen Namen oder soll diese nicht benutzt werden, wird der Messordner nach dem im cdict angegebenen pickle-ﬁle durchsucht und dieses geladen. In diesem Fall würde dann aus den in der pickle-Datei enthaltenen Daten die Instanz der Klasse

42

3 Messungen zur Untersuchung der Störfestigkeit MSC wieder erzeugt werden. Anschließend werden ab Zeile 151 dieser Instanz die Konﬁgurationen, measurement_parameters und evaluation_parameters aus dem cdict übergeben. Nun wird untersucht, ob in dieser Instanz bereits Messungen unter der description abgelegt sind, die für die aktuelle Messung laut Konﬁgurationsdatei benutzt werden sollen. Dies kann natürlich nur beim Laden eines alten pickle-ﬁles der Fall sein. Wird eine Messung gefunden, wird diese mit der entsprechenden description ausgegeben und in Zeile 176 abgefragt, wie weiter zu verfahren ist. Es besteht die Möglichkeit, die aktuelle Messung weiterzuführen (Continue). Weiterhin kann die aktuelle Messung abgebrochen und mit der Auswertung der vorhandenen Daten fortgefahren werden (Skip). Es ist es ebenfalls möglich, sowohl die aktuelle Messung als auch die Auswertung abzubrechen (Break) oder das Messprogramm komplett zu beenden (Exit). Wird ein Fortsetzen der Messungen gewählt, würde der alte Datensatz aus dem pickleﬁle überschrieben werden und die Routine msc.Measure_Immunity führt die Messung mit den in mp übergebenen Messparametern vom Zeitpunkt der erfolgten Sicherung an fort. Anschließend, bzw. wenn nur die Auswertung der Daten ausgewählt wurde, erfolgt in den Zeilen 201203 erst durch die Routine msc.OutputRawData_Immunity die Ausgabe der Rohdaten in die im Konﬁgurationsblock cdict unter rawdata_output_ﬁlename angegebene Datei, anschließend durch die Routine msc.Evaluate_Immunity mit den in ep übergebenen Parametern die Auswertung der Daten und schließlich durch durch die Routine msc.OutputProzessedData_Immunity die Ausgabe der ausgewerteten und geordneten Daten in die im Konﬁgurationsblock cdict unter prozesseddata_output_ﬁlename angegebene Datei. Sollten keine Sicherungsdateien vorhanden oder gewünscht werden, wird die eine neue Instanz der Klasse MSC erstellt und eine neue Messung mit den eben angesprochenen Routinen der Klasse MSC begonnen und anschließend ausgewertet. Diese Messung erhält dann als Bezeichnung den ersten Eintrag der Liste descriptions aus dem Konﬁgurationsblock. Die Messung wird dann für alle weiteren in description eingetragenen Bezeichnungen wiederholt. Nachdem mit der Ausgabe der Daten die Auswertung abgeschlossen ist, wird eine abschließende pickle-Datei angelegt, die alle bisherigen Messungen dieser Instanz der Klasse enthält, also die soeben beendete Messung samt Auswertung, sowie die, die in einer evtl. zuvor eingelesen Sicherungsdatei (Input-pickle-Datei oder autosavedatei) gespeichert waren. Der Name dieser Output-pickle-Datei wurde ebenfalls in der Konﬁgurationsdatei festgelegt. Zunächst wird in Zeile 218 geprüft, ob es bereits eine Datei unter diesem Namen gibt. Falls das der Fall ist, wird abgefragt, ob diese evtl. überschrieben werden soll, oder ob die neue pickle-Datei einfach an die vorhandene Datei angehängt werden soll. Nachdem die komplette Messung als Outputpickle-Datei gesichert wurde, wird letzlich noch die evtl. vorhanden Autosavedatei gelöscht, da sie ja durch die beendete Messung und Auswertung nicht benötig wird. Achtung: Wird die Messung aus einer Autosavedatei gestartet, wird nach Abschluss der Messung keine Aus-

43

3 Messungen zur Untersuchung der Störfestigkeit wertung ausgeführt, sondern nur das Output-pickle-ﬁle erstellt. In diesem Fall muss die Messung mit diesem Output-pickle-ﬁle als Input-pickle-ﬁle nocheinmal gestartet werden. Dann würde, wie oben beschrieben, die Meldung, dass im eingelesenen pickle-ﬁle bereits eine Messung mit der aktuellen description vorhanden ist und die Abfrage, was geschehen soll, erscheinen. Durch Auswahl von Skip wird dann die aktuelle Messung abgebrochen und es werden nur die vorhandenen Daten aus der gespeicherten Messung ausgewertet und man erhält so die Roh- und Ergebnisdaten. Das Messprogramm kann während der Messung jederzeit durch Drücken einer Taste gestoppt werden. Dies wird auch akustisch signalisiert. Der Ausgangssignal des Signalgenerators wird abgeschaltet, die Kammer kann also geöffnet und auch betreten werden. Gleichzeitig erfolgt eine Abfrage, wie weiter zu verfahren ist. Mit Continue kann die Messung fortgesetzt werden. Mit Suspend werden die Geräte vom Bus abgemeldet, die Instanz bleibt jedoch aktiv, da das Messprogramm auf weitere Eingaben wartet. Die Geräte können ausgeschaltet und auch aus dem Aufbau entfernt werden. Dies kann zum Beispiel genutzt werden, um die Akkus der Sonden zu laden oder Geräte kurzzeitig für andere Messungen zu benutzen, ohne dafür das Messprogramm unterbrechen zu müssen. Der Rechner darf jedoch während dieser Zeit nicht ausgeschaltet werden, da das Messprogramm ja noch läuft. Nachdem alle Geräte wieder angeschlossen und eingeschaltet sind, kann die Messung fortgesetzt werden. Hierzu werden alle Geräte neu initialisiert und die Messung läuft weiter. Mit Quit kann die Messung auch beendet werden. Abbildung 3.6 zeigt den Inhalt des Messordners nach Abschluss der Messung.

Abbildung 3.6: Messordnerinhalt nach Abschluss der Messungen Man sieht also zusätzlich die beiden Ausgabedateien out_raw_immunity-PCBoard1.dat und out_processed_immunity-PCBoard1.dat, sowie aus Output-pickle-ﬁle msc-immunity.p und die Protokolldatei msc.log.

44

A Deﬁnitionen
Im Listing A.1 ist die Datei defs.h aus dem Quelltext des Programms dargestellt. Hier ﬁndet sich eine Übersicht über alle Parameter mit ihrer korrekten Schreibweise, die in den Einträgen in den Initialisierungsdateien und Konﬁgurationsdateien als gültige Einträge akzeptiert werden. Begonnen wird mit den Einheiten, anschließend folgen die gültigen Parameter für die einzelnen Messgerätefamilien. Die Zahlen am Zeilenende werden bei der Programmierung der Treiber für den internen Umgang mit den Parametern verwendet und sollen hier nicht weiter interessieren. Listing A.1: Deﬁnition der erlaubten Parameternamen
1 2 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 38 39 # d e f i n e TRUE # d e f i n e FALSE // units # d e f i n e DIMENSIONLESS 0 # d e f i n e dBm 1 # define W 2 # d e f i n e dBuV 3 # define V 4 # d e f i n e dB 5 # d e f i n e Hz 6 # d e f i n e kHz 7 # d e f i n e MHz 8 # d e f i n e GHz 9 # d e f i n e Voverm 10 # d e f i n e dBVoverm 11 # d e f i n e METER 12 # d e f i n e CENTIMETER 13 # d e f i n e MILLIMETER 14 # d e f i n e deg 15 # d e f i n e r a d 16 # d e f i n e s t e p s 17 # d e f i n e dBoverm 18 # d e f i n e d B i 19 # d e f i n e dBd 20 # d e f i n e oneoverm 21 # d e f i n e Aoverm 22 # d e f i n e dBAoverm 23 # d e f i n e Woverm2 24 # d e f i n e dBWoverm2 25 # d e f i n e dBSoverm 27 # d e f i n e A m p l i t u d e R a t i o 28 # d e f i n e P o w e r R a t i o 29 # d e f i n e H 30 # d e f i n e F 31 # d e f i n e INTERPOL_LOG 1 # d e f i n e INTERPOL_LIN 2 / /W/ m^2 / / 1 0 ∗ l o g ( x / 1 [W/ m^ 2 ] ) 1 0

# d e f i n e Soverm 26 / / m a g n e t i c a n t e n n a f a c t o r

45

A Deﬁnitionen

41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57

/ / SG # d e f i n e AMSOURCE_INT # d e f i n e AMSOURCE_INT1 # d e f i n e AMSOURCE_INT2 # d e f i n e AMSOURCE_EXT # d e f i n e AMSOURCE_EXT1 # d e f i n e AMSOURCE_EXT2 # d e f i n e AMSOURCE_EXT_AC # d e f i n e AMSOURCE_EXT_DC 0 0 1 2 2 3 4 5

# d e f i n e AMSOURCE_TWOTONE_AC 6 # d e f i n e AMSOURCE_TWOTONE_DC 7 # d e f i n e AMSOURCE_OFF # d e f i n e LFSINE # d e f i n e LFSQUARE # d e f i n e LFTRIANGLE # d e f i n e LFPERIODIC_NOISE # d e f i n e LFSAWTOOTH 8 0 1 2 3 4

60 61 62 63 64 65 66 67 68

# d e f i n e PMSOURCE_INT

0

# d e f i n e PMSOURCE_EXT1 1 # d e f i n e PMSOURCE_EXT2 2 # d e f i n e PMSOURCE_OFF 3 # d e f i n e PMWAVEFORM_OFF 0 # d e f i n e PMWAVEFORM_SIN 1 # d e f i n e PMWAVEFORM_DOU 2 # d e f i n e PMWAVEFORM_TRI 3 # d e f i n e PMWAVEFORM_QUA 4

71 72

# d e f i n e PMPOLNORMAL

0

# d e f i n e PMPOLINVERTED 1

75 76 77 78 79 81 82 83 85 86 87 88 89 90 92 93 95 96 97 98 99 100 101 103 104 106 107 108 109 110 112 113 115

/ / PM # d e f i n e RANGEAUTO # d e f i n e RANGEMANUAL # d e f i n e FILTERAUTO / / SW q u i t d e f s # d e f i n e SW_QUIT_LATCHING 0 # d e f i n e SW_QUIT_NON_LATCHING 1 / / PROBE # d e f i n e COMP_X 0 # d e f i n e COMP_Y 1 # d e f i n e COMP_Z 2 # d e f i n e COMP_R 3 # d e f i n e ALL_VALUES 4 / / Tuner # d e f i n e MAXNTUNERS 8 / / Antenna # d e f i n e ANT_FACTOR 0 # d e f i n e ANT_GAIN # d e f i n e ANT_EFF # d e f i n e EFIELD 0 # d e f i n e HFIELD 1 / / NPORT # d e f i n e MAX_PORTS 6 / / Amplifier # d e f i n e AMP_IN # d e f i n e AMP_FWD # d e f i n e AMP_BWD 0 1 2 1 2 1 0 −1 # d e f i n e RANGEAUTOONCE 2

# d e f i n e MAX_ANT_XXX 10

# d e f i n e MAX_AMP_XXX 10 # d e f i n e CTRL_LOCAL 0

# d e f i n e CTRL_REMOTE 1 # d e f i n e MODE_MAN 0

46

A Deﬁnitionen

116 117 119 120 122 123 124 125 127 128 129 130 131 132 133 134 135 136 137 138 139 140 141 142 143 144

# d e f i n e MODE_PULSE 1 # d e f i n e MODE_ALC 2

# d e f i n e ALC_DET_INT 0 # d e f i n e ALC_DET_EXT 1 # d e f i n e AMP_POFF # d e f i n e AMP_PON # d e f i n e AMP_STANDBY # d e f i n e AMP_OPERATE / / SA # d e f i n e ATT_AUTO_NORMAL 0 # d e f i n e ATT_AUTO_LowNoise 1 # d e f i n e ATT_AUTO_LowDist 2 # d e f i n e DET_AUTOSELECT 0 # d e f i n e DET_AUTOPEAK 1 # d e f i n e DET_MAXPEAK 2 # d e f i n e DET_MINPEAK 3 # d e f i n e DET_SAMPLE 4 # d e f i n e DET_RMS 5 # d e f i n e DET_AVERAGE 6 # d e f i n e DET_QPEAK 7 # d e f i n e TR_WRITE 0 # d e f i n e TR_VIEW 1 # d e f i n e TR_AVERAGE 2 # d e f i n e TR_BLANK 3 # d e f i n e TR_MAXHOLD 4 # d e f i n e TR_MINHOLD 5 0 1 2 3

148 149 150 151 152 153 155 156 157 158 159 160 161 162 164 165 166 167 168 169 170 171 172 173 174 175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190

/ / Tokens and s e c t i o n Names # d e f i n e SEC_DESC " d e s c r i p t i o n " # d e f i n e SEC_INIT " INIT_VALUE " # d e f i n e SEC_CHANNEL "CHANNEL_" / / # d e f i n e SEC_ANT_FAC { " ANTENNA_FACTOR " , " ANTENNA_GAIN " , " ANTENNA_EFFICENCY " } / / # d e f i n e SEC_AMP_FAC { " MAX_INP_LEVEL " , " MAX_FWD_LEVEL " , " MAX_BWD_LEVEL " } # d e f i n e TOK_DESC " DESCRIPTION " # d e f i n e TOK_VENDOR "VENDOR" # d e f i n e TOK_TYPE " TYPE " # d e f i n e TOK_SN " SERIALNR " # d e f i n e TOK_DEVID " DEVICEID " # d e f i n e TOK_DRIVER " DRIVER " # d e f i n e TOK_NCHANNELS "NR_OF_CHANNELS" # d e f i n e TOK_NAME "NAME" # d e f i n e TOK_FSTART " FSTART " # d e f i n e TOK_FSTOP "FSTOP" # d e f i n e TOK_FSTEP " FSTEP " # d e f i n e TOK_GPIB " GPIB " / / 1= v i r t u a l e l s e r e a l / / ( SG ) / / ( SG ) / / ( SG ) / / 1=TF On e l s e O f f ( SG ) ( SG ) ( SG ) # d e f i n e TOK_VIRTUAL " VIRTUAL " # d e f i n e TOK_CHNAME "NAME" # d e f i n e TOK_LEVEL " LEVEL" # d e f i n e TOK_LEVOFFSET "LEVELOFFSET" # d e f i n e TOK_LEVLIMIT " LEVELLIMIT " # d e f i n e TOK_OUTPUTSTATE "OUTPUTSTATE"

# d e f i n e TOK_LFOUTPUTSTATE "LFOUTPUTSTATE" / / 1=LF On e l s e O f f # d e f i n e TOK_ATTMODE "ATTMODE" # d e f i n e TOK_UNIT " UNIT " # d e f i n e TOK_ATTENUATION "ATTENUATION" / / ( SG ) , PM , SA # d e f i n e TOK_CHANNEL "CHANNEL" # d e f i n e TOK_AMSTATE "AMSTATE" # d e f i n e TOK_AMDEPTH "AMDEPTH" # d e f i n e TOK_AMFREQ "AMFREQ" # d e f i n e TOK_AMSOURCE "AMSOURCE" # d e f i n e TOK_AMPOLARITY "AMPOLARITY" # d e f i n e TOK_PMSTATE "PMSTATE" # d e f i n e TOK_PMSOURCE "PMSOURCE" # d e f i n e TOK_PMPOLARITY "PMPOLARITY" # d e f i n e TOK_PMWIDTH "PMWIDTH" # d e f i n e TOK_PMDELAY "PMDELAY" / / depth in % / / AM −f i n Hz

# d e f i n e TOK_OPERATINGMODE "OPERATINGMODE" / / 0=normal , e l s e sweep ( SG ) / / 1= f i x e d , e l s e a u t o / / see top of f i l e

/ / 0 : O f f , e l s e On

/ / 0 : i n t 1 , 1 : i n t 2 , e l s e e x t ( SMT ) / / 0 : normal , e l s e i n v e r t e d / / 0 : O f f , e l s e On / / 0: int , e l s e ext / / 0 : normal , e l s e i n v e r t e d (SMR & SMT )

# d e f i n e TOK_AMEXTCOUPLING "AMEXTCOUPLING" / / 0 : AC , e l s e DC

47

A Deﬁnitionen

191 192 193 194 195 196 197 198 199 200 201 202 203 204 205 206 207 208 209 210 211 212 213 214 215 216 217 218 219 220 221 222 223 224 225 226 227 228 229 230 231 232 233 234 236 237 239 240 241 242 243 244 245 246 248 249 250 251 252 253 254 255 257 258 259 260 261 263 264 265

# d e f i n e TOK_PMFREQ "PMFREQ" # d e f i n e TOK_PMWAVEFORM "PMWAVEFORM" # d e f i n e TOK_RANGEMODE "RANGEMODE" # d e f i n e TOK_FILTER " FILTER " # d e f i n e TOK_MANRANGE "MANRANGE" # d e f i n e TOK_SENSOR "SENSOR" # d e f i n e TOK_SWR "SWR" # d e f i n e TOK_RESOLUTION "RESOLUTION" # d e f i n e TOK_INTERPOLATION " INTERPOLATION " # d e f i n e TOK_FILE " FILE " # d e f i n e TOK_CTRL_TYPE " CTRL_TYPE " # d e f i n e TOK_IN_REG " IN_REG " # d e f i n e TOK_OUT_REG "OUT_REG" # d e f i n e TOK_NR_SW_DEV " NR_OF_SWITCHING_DEVICES " # d e f i n e TOK_SELFTEST " SELFTEST " # d e f i n e TOK_MASK "MASK" # d e f i n e TOK_STAT " STAT_ " # d e f i n e TOK_SNAME " NSTAT_ " # d e f i n e TOK_DIRECT " DIRECT " # d e f i n e TOK_FSTART " FSTART " # d e f i n e TOK_FSTOP "FSTOP" # d e f i n e TOK_FSTEP " FSTEP " # d e f i n e TOK_SPS " SPS " # d e f i n e TOK_CPS "CPS" # d e f i n e TOK_TMIN "TMIN" # d e f i n e TOK_TSEC " TSEC " # d e f i n e TOK_TTENTH "TTENTH" # d e f i n e TOK_DDE "DDEPATH" # d e f i n e TOK_SERVER "DDESERVERNAME" # d e f i n e TOK_PRB "PROBE" # d e f i n e TOK_COM "COM" # d e f i n e TOK_PARITY " PARITY " # d e f i n e TOK_XON "XON" # d e f i n e TOK_ZERO "AUTO_ZERO" # d e f i n e TOK_ZERO_TIME "AUTO_ZERO_TIME" # d e f i n e TOK_SAMPLE_FREQ "SAMPLE_FREQ" # d e f i n e TOK_MEASURE_VALUE "MEASURE_VALUE" # d e f i n e TOK_MEASURE_UNIT "MEASURE_UNIT" # d e f i n e TOK_MEASURE_ARRAY "MEASURE_ARRAY" # d e f i n e TOK_AVERAGE "AVERAGE" # d e f i n e TOK_AVERAGE_TIME "AVERAGE_TIME" # d e f i n e TOK_AVERAGE_NR "AVERAGE_NR" # d e f i n e TOK_SENSORTYPE " SENSOR_TYPE " # d e f i n e TOK_MODE "MODE" / / Antenna # d e f i n e TOK_FIELD " FIELD " / / Motorcontroller # d e f i n e TOK_MIN "MIN" # d e f i n e TOK_MAX "MAX" # d e f i n e TOK_STEP " STEP " # d e f i n e TOK_SPEED "SPEED" # d e f i n e TOK_DOWN # d e f i n e TOK_UP "DOWNCOMMAND" "UPCOMMAND" / / PM: a u t o i s t d e f i n e d by FILTERAUTO , o t h e r v a l u e s d e p e n d on i n s t r u m e n t

# d e f i n e TOK_CANGOOVERZERO "CANGOOVERZERO" / / Amplifier # d e f i n e TOK_CONTROL "CONTROL" # d e f i n e TOK_MODE "MODE" # d e f i n e TOK_DETECTOR "DETECTOR" # d e f i n e TOK_RFGAIN "RFGAIN" / / in percent / / value is device s p e c i f i c / / value is device s p e c i f i c / / value is device s p e c i f i c # d e f i n e TOK_ALCTHRESHOLD "ALCTHRESHOLD" # d e f i n e TOK_ALCRESPONSE "ALCRESPONSE" / /COM # d e f i n e TOK_RATE "COMRATE" # d e f i n e TOK_DATA " DATABITS " # d e f i n e TOK_PARITY " PARITY " # d e f i n e TOK_STOPBIT " STOPBITS " / / Network a n a l y s e r # d e f i n e TOK_SOURCE "SOURCE" # d e f i n e TOK_READ "READ"

# d e f i n e TOK_ALCDETECTORGAIN "ALCDETECTORGAIN"

48

A Deﬁnitionen

267 268 269 270 271 273 274 275 276 277 278 279 281 282 283 284 285 286 288 290 291 292 293 294 295 296 298 299 300

# d e f i n e NO_PARITY # d e f i n e ODD_PARITY # d e f i n e EVEN_PARITY # d e f i n e MARK_PARITY

0 1 2 3

# d e f i n e SPACE_PARITY 4 / / SA # d e f i n e TOK_REFLEVEL "REFLEVEL" # d e f i n e TOK_RBW "RBW" # d e f i n e TOK_VBW "VBW" # d e f i n e TOK_SPAN "SPAN" # d e f i n e TOK_TRACE "TRACE" # d e f i n e TOK_TRACEMODE "TRACEMODE" # d e f i n e T_MAX "MAX" # d e f i n e T_MIN "MIN" # d e f i n e T_WRITE " WRITE" # d e f i n e T_VIEW "VIEW" # d e f i n e T_AVERAGE "AVERAGE" # d e f i n e T_BLANK "BLANK" # d e f i n e TOK_DETECTOR "DETECTOR" # d e f i n e D_QPEAK "QPEAK" # d e f i n e D_APEAK "AUTOPEAK" # d e f i n e D_SAMPLE "SAMPLE" # d e f i n e D_RMS "RMS" # d e f i n e D_AVERAGE "AVERAGE" # d e f i n e D_MAX "POS" # d e f i n e D_MIN "NEG" # d e f i n e TOK_SWEEPCOUNT "SWEEPCOUNT" # d e f i n e TOK_FREERUN "FREERUN" # d e f i n e TOK_SWEEPTIME "SWEEPTIME"

304 305

# d e f i n e MIN ( x , y ) # d e f i n e MAX( x , y )

( ( x ) <( y ) ? ( x ) : ( y ) ) ( ( x ) >( y ) ? ( x ) : ( y ) )

49

A Deﬁnitionen

Kontakt: Dr. rer. nat. H. G. Krauthäuser Otto-von-Guericke-Universität Magdeburg Fakultät für Elektrotechnik und Informationstechnik Institut für Grundlagen der Elektrotechnik und Elektromagnetische Verträglichkeit Universitätsplatz 2 39106 Magdeburg Tel.: 0391/67-12195 mail: hgk@E-Technik.uni-magdeburg.de

50

