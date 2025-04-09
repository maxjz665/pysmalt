import numpy as np
import csv
import xlsxwriter
import math
xlsxNAME = 'exp3t.xlsx'
AUTHOR = 'EXP3'
allText = [
    154, #155, 157, 164, 165, 166, 167, 200, 205,  # Достоевский
    #245, 246, 247, 248,  # Щебальский
    #146, 151, 152, 181, 182, 183, 184, 185, 222, 223, 235,  # Мещерский
    159  # Дубия'''
           ]
trainText = [154] #, 155, 157, 164, 165, 166, 167, 200, 205]
# allText = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33]
# trainText = [1,2,3,4,5,6]
COUNT = len(allText)
# print(COUNT)

LENGTH = 500
SENT = 30

#######################################################################################################################
# 1 - 8

parts = ["существительное", "прилагательное", "числительное", "местоимение", "глагол", "причастие",
         "деепричастие", "наречие", "кат.состояния", "частица", "предлог", "союз", "модальное", "междометие",
         "звукоподражательное", "иностранное", "цитата", "вводное", "старославянизм", "фразеологизм",
         "неязыковой", "сокращённое", "многочленное", "заголовок"]
partLen = len(parts)
# Прочитка текстов и создание "номеров"
data = list()
name = list()

######### TODO Чтение текстов
for text in range(COUNT):
    data.append([])
    sentFlag = True
    sentence = list()
    sentCounter = 0
    wordCounter = 0
    name.append([])
    with open(AUTHOR + '_csv/' + str(allText[text]) + '.csv', encoding='UTF-8', newline='') as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                            quoting=csv.QUOTE_NONE)
        # print(AUTHOR + '_csv/' + str(allText[text]) + '.csv', encoding='UTF-8', newline='')
        for row in reader:
            row[0] = row[0].replace('"', '').strip()
            row[1] = row[1].replace('"', '').strip()
            row[2] = row[2].replace('"', '').strip()
            if row[0] != "":
                sentFlag = False
                sentence.append(row[2])
                wordCounter += 1
                if wordCounter < 7:
                    name[text].append(row[0])
            else:
                if sentFlag:
                    continue
                sentFlag = True
                length = len(sentence)
                # print(length)
                if length < 3:
                    sentence.clear()
                    continue
                # print(sentence)
                data[text].append(list())
                data[text][sentCounter].append(sentence[0])
                data[text][sentCounter].append(sentence[1])
                data[text][sentCounter].append(sentence[length - 3])
                data[text][sentCounter].append(sentence[length - 2])
                data[text][sentCounter].append(sentence[length - 1])
                sentCounter += 1
                sentence.clear()

# print(len(data))


#######################################################################################################################
# 9
finalTable9 = list()
finalTable9.append(['Текст', 'Кол.Отрыв', 'ср.длина', 'ср.дисп', 'ср.откл', 'отклонение', 'дисперсия', 'sd', 't'])
# Строки результатов
result = list()
# Число строк результатов
nRow = 0

for text in range(COUNT):
    # Сам текст (словами)
    mass = list()
    with open(AUTHOR + '_csv/' + str(allText[text]) + '.csv', encoding='UTF-8', newline='') as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                            quoting=csv.QUOTE_NONE)
        # print(AUTHOR + '_csv/' + str(allText[text]) + '.csv', encoding='UTF-8', newline='')
        # Число слов в отрывке
        counter = 0
        for row in reader:
            row[0] = row[0].replace('"', '').strip()
            row[1] = row[1].replace('"', '').strip()
            row[2] = row[2].replace('"', '').strip()
            # print(row, len(row))
            if row[0] != "":
                counter += 1
                mass.append(len(row[0]))

            if counter == LENGTH:
                # Номер текста - среднее значение на участке
                result.append([text, np.mean(mass), np.var(mass), np.std(mass)])
                mass.clear()
                counter = 0
                nRow += 1

coTRAIN = 0
meTRAIN = 0
vaTRAIN = 0
stTRAIN = 0
for i in range(len(result)):
    # print(result[i])
    if allText[result[i][0]] in trainText:
        coTRAIN += 1
        meTRAIN += result[i][1]
        vaTRAIN += result[i][2]
        stTRAIN += result[i][3]
mTRAIN = meTRAIN / coTRAIN
meanMassTrain = list()
for i in range(len(result)):
    if allText[result[i][0]] in trainText:
        meanMassTrain.append(result[i][1])
# среднеквадратичное (стандартное) отклонение
sTRAIN = np.std(meanMassTrain)
# дисперсию значений
dTRAIN = np.var(meanMassTrain)
# print('TRAIN', coTRAIN, mTRAIN, vaTRAIN / coTRAIN, stTRAIN / coTRAIN, dTRAIN, sTRAIN)
finalTable9.append(['TRAIN', coTRAIN, mTRAIN, vaTRAIN / coTRAIN, stTRAIN / coTRAIN, dTRAIN, sTRAIN])

currentText = 0
while currentText < COUNT:
    coTEST = 0
    meTEST = 0
    vaTEST = 0
    stTEST = 0
    for i in range(len(result)):
        if result[i][0] == currentText:
            coTEST += 1
            meTEST += result[i][1]
            vaTEST += result[i][2]
            stTEST += result[i][3]

    mTEST = meTEST / coTEST
    meanMassTest = list()
    for i in range(len(result)):
        if result[i][0] == currentText:
            meanMassTest.append(result[i][1])

    sTEST = np.std(meanMassTest)
    dTEST = np.var(meanMassTest)

    sd = np.sqrt(((coTRAIN - 1) * dTRAIN + (coTEST - 1) * dTEST) / (coTRAIN + coTEST - 2))
    answer = ((mTEST - mTRAIN) / sd * np.sqrt(coTRAIN * coTEST / (coTRAIN + coTEST)))
    # print('#' + str(currentText), coTEST, mTEST, vaTEST / coTEST, stTEST / coTEST, dTEST, sTEST, 'sd =', sd, 'answer =', answer)
    finalTable9.append(['#' + str(currentText), coTEST, mTEST, vaTEST / coTEST, stTEST / coTEST, dTEST, sTEST, sd, answer])

    currentText += 1

#######################################################################################################################
# 10

# Строки результатов
result = list()
# Число строк результатов
nRow = 0
# Число слов в отрывке
counter = [0] * (COUNT + 1)

for i in range(COUNT):
    with open(AUTHOR + '_csv/' + str(allText[i]) + '.csv', encoding='UTF-8', newline='') as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                            quoting=csv.QUOTE_NONE)
        wordLen = [i, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        for row in reader:
            row[0] = row[0].replace('"', '').strip()
            row[1] = row[1].replace('"', '').strip()
            row[2] = row[2].replace('"', '').strip()
            if row[0] != "":
                counter[i] += 1
                WL = len(row[0])
                if WL < 16:
                    wordLen[WL] += 1
                else:
                    wordLen[16] += 1

        result.append(wordLen)
        wordLen = [i, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        nRow += 1
# for i in range(nRow):
    # print(result[i], counter[i])

train = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
p1 = list()
p1n = list()
pSum1 = 0
trainCounter = 0
for i in range(len(result)):
    if allText[result[i][0]] not in trainText:
        # print(i, 'CONTINUE')
        continue
    trainCounter += counter[i]
    for j in range(16):
        train[j] += result[i][j + 1]
for j in range(16):
    p1.append(train[j] / trainCounter)
    pSum1 += p1[j]
    p1n.append(pSum1)
# print('P(tr) = ', p1)
# print('Pn(tr) = ', p1n, len(p1n))

p2 = list()
p2n = list()
d = list()
pSum2 = list()
alpha10 = list()

for i in range(nRow):
    # print('----------' + str(i) + '----------')
    p2.append(list())
    p2n.append(list())
    d.append(list())
    pSum2.append(0)

    for j in range(16):
        p2[i].append(result[i][j+1] / counter[i])
        pSum2[i] += p2[i][j]
        p2n[i].append(pSum2[i])
        d[i].append(abs(p1n[j] - p2n[i][j]))
    # print('Pn(', str(i), ') = ', p2n[i])
    alpha10.append(max(d[i]) * np.sqrt(trainCounter * counter[i] / (trainCounter + counter[i])))
    # print('d', max(d[i]))
    # print(d[i])
    # print('lambda', alpha10[i], trainCounter, counter[i])

# together = list()
# together.append(['#', 'kod', 'name', 'lambda', 'max(d)', 'Кол-во', 'Вер-ти', 'Накопит', 'd'])
# together.append(['Tr','kod', 'name', '-', '-', trainCounter, p1, p1n])
# for i in range(COUNT):
#     together.append([i+1, 'kod', 'name', alpha10[i], max(d[i]), counter[i], p2[i], p2n[i], d[i]])

#######################################################################################################################
# 11
finalTable11 = list()
finalTable11.append(['Текст', 'Кол.Отрыв', 'ср.длина', 'ср.дисп', 'ср.откл', 'отклонение', 'дисперсия', 'sd', 't'])

# Строки результатов
result = list()
# Число строк результатов
nRow = 0
sflag = True
sent0Mean = list()
sent1Mean = list()

for i in range(COUNT):
    # Сам текст
    mass = list()
    wCounter = 0
    sCounter = 0
    with open(AUTHOR + '_csv/' + str(allText[i]) + '.csv', encoding='UTF-8', newline='') as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                            quoting=csv.QUOTE_NONE)
        for row in reader:
            row[0] = row[0].replace('"', '').strip()
            row[1] = row[1].replace('"', '').strip()
            row[2] = row[2].replace('"', '').strip()
            if row[0] != "":
                wCounter += 1
                sflag = False
            else:
                if sflag:
                    continue
                sflag = True
                # print(wCounter, sCounter, i, mass)
                sCounter += 1
                mass.append(wCounter)
                wCounter = 0


            if sCounter == SENT:
                # Номер текста - среднее значение на участке
                # print(i, mass, np.mean(mass))
                result.append([i, np.mean(mass), np.var(mass), np.std(mass)])
                # print(result)
                mass.clear()
                sCounter = 0
                nRow += 1

# print(result)

'''with open('res11/' + AUTHOR + 'отрывки.csv', mode="w", encoding='utf-8') as w_file:
    file_writer = csv.writer(w_file, delimiter=",", lineterminator="\r")
    file_writer.writerow(['#', 'mean', 'var', 'std'])
    for i in range(nRow):
        file_writer.writerow(result[i])'''

coTRAIN = 0
meTRAIN = 0
vaTRAIN = 0
stTRAIN = 0
for i in range(len(result)):
    if allText[result[i][0]] in trainText:
        coTRAIN += 1
        meTRAIN += result[i][1]
        vaTRAIN += result[i][2]
        stTRAIN += result[i][3]
mTRAIN = meTRAIN / coTRAIN
meanMassTrain = list()
for i in range(len(result)):
    if allText[result[i][0]] in trainText:
        meanMassTrain.append(result[i][1])
# среднеквадратичное (стандартное) отклонение
sTRAIN = np.std(meanMassTrain)
# дисперсию значений
dTRAIN = np.var(meanMassTrain)
# print('TRAIN', coTRAIN, mTRAIN, vaTRAIN / coTRAIN, stTRAIN / coTRAIN, dTRAIN, sTRAIN)
finalTable11.append(['TRAIN', coTRAIN, mTRAIN, vaTRAIN / coTRAIN, stTRAIN / coTRAIN, dTRAIN, sTRAIN])

currentText = 0
while currentText < COUNT:
    coTEST = 0
    meTEST = 0
    vaTEST = 0
    stTEST = 0
    # print(len(result))
    for i in range(len(result)):
        if result[i][0] == currentText:
            coTEST += 1
            meTEST += result[i][1]
            vaTEST += result[i][2]
            stTEST += result[i][3]

    mTEST = meTEST / coTEST
    meanMassTest = list()
    for i in range(len(result)):
        if result[i][0] == currentText:
            meanMassTest.append(result[i][1])

    sTEST = np.std(meanMassTest)
    dTEST = np.var(meanMassTest)

    sd = np.sqrt(((coTRAIN - 1) * dTRAIN + (coTEST - 1) * dTEST) / (coTRAIN + coTEST - 2))
    answer = ((mTEST - mTRAIN) / sd * np.sqrt(coTRAIN * coTEST / (coTRAIN + coTEST)))
    # print('#' + str(currentText), coTEST, mTEST, vaTEST / coTEST, stTEST / coTEST, dTEST, sTEST, 'sd =', sd, 'answer =', answer)
    finalTable11.append(['#' + str(currentText), coTEST, mTEST, vaTEST / coTEST, stTEST / coTEST, dTEST, sTEST, sd, answer])
    currentText += 1

#######################################################################################################################
# 12
# Количество промежутков по 5 (1-5, 6-10 ...)
fiveParts = 13
# Строки результатов
result = list()
sFlag = True
f = list()
p = list()
pn = list()
d = [0] * fiveParts
sCounter = [0] * COUNT

for i in range(COUNT):
    f.append([0] * fiveParts)
    wCounter = 0
    with open(AUTHOR + '_csv/' + str(allText[i]) + '.csv', encoding='UTF-8', newline='') as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                            quoting=csv.QUOTE_NONE)
        for row in reader:
            row[0] = row[0].replace('"', '').strip()
            row[1] = row[1].replace('"', '').strip()
            row[2] = row[2].replace('"', '').strip()
            if row[0] != "":
                wCounter += 1
                sFlag = False
            else:
                if sFlag:
                    continue
                sFlag = True
                sCounter[i] += 1
                if wCounter > 64:
                    wCounter = 64
                f[i][math.ceil(wCounter / 5) - 1] += 1
                wCounter = 0
    p.append([0] * fiveParts)
    pn.append([0] * fiveParts)

# print(f)

train = [0] * fiveParts
p1 = list()
p1n = list()
pSum1 = 0
trainCounter = 0
for i in range(len(f)):
    result.append([i] + f[i])
    if allText[result[i][0]] not in trainText:
        # print(i, 'CONTINUE')
        continue
    trainCounter += sCounter[i]
    for j in range(fiveParts):
        train[j] += result[i][j + 1]
for j in range(fiveParts):
    p1.append(train[j] / trainCounter)
    pSum1 += p1[j]
    p1n.append(pSum1)
# print('P(tr) = ', p1)
# print('Pn(tr) = ', p1n, len(p1n))

p2 = list()
p2n = list()
d = list()
pSum2 = list()
alpha12 = list()

for i in range(COUNT):
    # print('----------' + str(i) + '----------')
    p2.append(list())
    p2n.append(list())
    d.append(list())
    pSum2.append(0)

    for j in range(fiveParts):
        p2[i].append(result[i][j + 1] / sCounter[i])
        pSum2[i] += p2[i][j]
        p2n[i].append(pSum2[i])
        d[i].append(abs(p1n[j] - p2n[i][j]))
    # print('Pn(', str(i), ') = ', p2n[i])
    alpha12.append(max(d[i]) * np.sqrt(trainCounter * sCounter[i] / (trainCounter + sCounter[i])))
    # print('d', max(d[i]))
    # print(d[i])
    # print('lambda', alpha12[i], trainCounter, sCounter[i])

'''together = list()
together.append(['#', 'kod', 'name', 'lambda', 'max(d)', 'Кол-во', 'Вер-ти', 'Накопит', 'd'])
together.append(['Tr', 'kod', 'name', '-', '-', trainCounter, p1, p1n])
for i in range(COUNT):
    together.append([i + 1, 'kod', 'name', alpha12[i], max(d[i]), sCounter[i], p2[i], p2n[i], d[i]])
'''
#######################################################################################################################
# 13
spek = list()
partCounter = [0] * COUNT
wordCounter = [0] * COUNT
totalCounter = [0] * COUNT
devi = 10

for i in range(COUNT):
    text = list()
    counter = 0
    spek.append([0] * devi)
    with open(AUTHOR + '_csv/' + str(allText[i]) + '.csv', encoding='UTF-8', newline='') as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                        quoting=csv.QUOTE_NONE)
        for row in reader:
            row[0] = row[0].replace('"', '').strip()
            row[1] = row[1].replace('"', '').strip()
            row[2] = row[2].replace('"', '').strip()
            if row[0] != "":
                counter += 1
                text.append(row[0].lower())
            if counter == LENGTH:
                partCounter[i] += 1
                yet = list()
                for word in text:
                    if word in yet:
                        continue
                    yet.append(word)
                    col = text.count(word)

                    if col > devi:
                        col = devi
                    spek[i][col-1] += 1
                    wordCounter[i] += col
                counter = 0
                text.clear()
p = list()
pn = list()
d = list()
tp = list()
tpn = list()
spekSum = 0
maxD = [0] * len(spek)
ld13 = [0] * len(spek)
trainParts = 0

for i in range(COUNT):
    for j in range(devi):
        totalCounter[i] += spek[i][j]
    # totalCounter[i] += length * partCounter[i] - totalCounter[i]
    # print(length * partCounter[i] - totalCounter[i])

# print(totalCounter)

spekSum = 0
# Данные по всем эталонным текстам
trainSpek = [0] * devi
trainTotal = 0
# Склеиваем
for i in range(len(spek)):
    if allText[i] not in trainText:
        continue
    for j in range(devi):
        trainSpek[j] += spek[i][j] #  * (j + 1)
    trainTotal += totalCounter[i]
    trainParts += partCounter[i]
# print(trainTotal, 'Train', trainSpek)
sum = 0
for j in range(devi):
    tp.append(trainSpek[j] / trainTotal)
    sum += tp[j]
    tpn.append(sum)

for i in range(len(spek)):
    spekSum = 0
    # print(partCounter[i], spek[i])
    # print(wordCounter[i], totalCounter[i])
    p.append([])
    pn.append([])
    sum = 0
    for j in range(devi):
        p[i].append(spek[i][j] / totalCounter[i])
        sum += p[i][j]
        pn[i].append(sum)
    # print(i, 'TOTAL', totalCounter[i])
# print('tpn', tp)
# print('pn', p[1])
for i in range(len(spek)):
    d.append([])
    for j in range(devi):
        d[i].append(abs(tpn[j] - pn[i][j]))
    maxD[i] = max(d[i])
    ld13[i] = maxD[i] * np.sqrt(trainTotal * totalCounter[i] / (trainTotal + totalCounter[i]))
#######################################################################################################################
# 14
spek = list()
partCounter = [0] * COUNT
wordCounter = [0] * COUNT
totalCounter = [0] * COUNT
devi = 10

for i in range(COUNT):
    text = list()
    counter = 0
    spek.append([0] * devi)

    with open(AUTHOR + '_csv/' + str(allText[i]) + '.csv', encoding='UTF-8', newline='') as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                            quoting=csv.QUOTE_NONE)
        for row in reader:
            row[0] = row[0].replace('"', '').strip()
            row[1] = row[1].replace('"', '').strip()
            row[2] = row[2].replace('"', '').strip()
            if row[0] != "":
                counter += 1
                totalCounter[i] += 1
                text.append(row[0].lower())
            if counter == LENGTH:
                partCounter[i] += 1
                yet = list()
                for word in text:
                    if word in yet:
                        continue
                    yet.append(word)
                    col = text.count(word)
                    if col > devi:
                        col = devi
                    spek[i][col-1] += 1
                    wordCounter[i] += col
                counter = 0
                text.clear()
p = list()
pn = list()
d = list()
tp = list()
tpn = list()
mfSum = 0
maxD = [0] * len(spek)
ld14 = [0] * len(spek)

mf = list()
for i in range(len(spek)):
    mf.append([])
    mfSum = 0
    for j in range(devi - 1):
        mf[i].append(spek[i][j] * (j + 1))
        mfSum += spek[i][j] * (j + 1)
    mf[i].append(partCounter[i] * LENGTH - mfSum)
# print(mf[0])
# print(mf[1])

mfSum = 0
# Данные по всем эталонным текстам
trainSpek = [0] * devi
trainTotal = 0
# Склеиваем
for i in range(len(mf)):
    if allText[i] not in trainText:
        continue
    for j in range(devi):
        trainSpek[j] += mf[i][j] #  * (j + 1)
    trainTotal += partCounter[i] * LENGTH
# print(trainTotal, 'Train', trainSpek)
sum = 0
for j in range(devi):
    tp.append(trainSpek[j] / trainTotal)
    sum += tp[j]
    tpn.append(sum)
# print(tp)
# print(tpn)

for i in range(len(mf)):
    mfSum = 0
    # print(partCounter[i], mf[i])
    # print(wordCounter[i], totalCounter[i])
    totalCounter[i] = partCounter[i] * LENGTH
    p.append([])
    pn.append([])
    sum = 0
    for j in range(devi):
        p[i].append(mf[i][j] / totalCounter[i])
        sum += p[i][j]
        pn[i].append(sum)
    # print(totalCounter[i])
for i in range(len(mf)):
    d.append([])
    for j in range(devi):
        d[i].append(abs(tpn[j] - pn[i][j]))
    maxD[i] = max(d[i])
    ld14[i] = maxD[i] * np.sqrt(trainTotal * totalCounter[i] / (trainTotal + totalCounter[i]))
    # print(d[i])
    # print(maxD[i], ld14[i])

#######################################################################################################################
# 15
res15 = list()

# Строки результатов
partlen = list()
partlen0 = list()
# Число строк результатов
nRow = 0

for i in range(COUNT):
    # Сам текст (словами)
    mass = list()
    with open(AUTHOR + '_csv/' + str(allText[i]) + '.csv', encoding='UTF-8', newline='') as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                            quoting=csv.QUOTE_NONE)
        # Число слов в отрывке
        counter = 0
        for row in reader:
            row[0] = row[0].replace('"', '').strip()
            row[1] = row[1].replace('"', '').strip()
            row[2] = row[2].replace('"', '').strip()
            if row[0] != "":
                counter += 1
                if not row[1].lower() in mass:
                    mass.append(row[0].lower())

            if counter == LENGTH:
                if allText[i] in trainText:
                    partlen0.append(len(mass))
                # Номер текста - среднее значение на участке
                partlen.append([i, len(mass)])
                mass.clear()
                counter = 0
                nRow += 1

mean0 = np.mean(partlen0)
var0 = np.var(partlen0)
n0 = len(partlen0)
# print(partlen0)
# print('mean0, var0, n0')
# print(mean0, var0, n0)

for i in range(COUNT):
    partlen1 = list()
    for part in partlen:
        if i == part[0]:
            partlen1.append(part[1])
    mean1 = np.mean(partlen1)
    var1 = np.var(partlen1)
    n1 = len(partlen1)

    sd = np.sqrt(((n0 - 1) * var0 + (n1 - 1) * var1) / (n1 + n0 - 2))
    answer = ((mean1 - mean0) / sd * np.sqrt(n1 * n0 / (n0 + n1)))

    res15.append([i, n1, mean1, var1, sd, answer])

# print(res15)

#######################################################################################################################
# 13mod
spek = list()
partCounter = [0] * COUNT
wordCounter = [0] * COUNT
totalCounter = [0] * COUNT
devi = 10

for i in range(COUNT):
    text = list()
    counter = 0
    spek.append([0] * devi)
    with open(AUTHOR + '_csv/' + str(allText[i]) + '.csv', encoding='UTF-8', newline='') as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                        quoting=csv.QUOTE_NONE)
        for row in reader:
            row[0] = row[0].replace('"', '').strip()
            row[1] = row[1].replace('"', '').strip()
            row[2] = row[2].replace('"', '').strip()
            if row[0] != "":
                counter += 1
                text.append(row[1].lower())
            if counter == LENGTH:
                partCounter[i] += 1
                yet = list()
                for word in text:
                    if word in yet:
                        continue
                    yet.append(word)
                    col = text.count(word)

                    if col > devi:
                        col = devi
                    spek[i][col-1] += 1
                    wordCounter[i] += col
                counter = 0
                text.clear()
p = list()
pn = list()
d = list()
tp = list()
tpn = list()
spekSum = 0
maxD = [0] * len(spek)
ld13m = [0] * len(spek)
trainParts = 0

for i in range(COUNT):
    for j in range(devi):
        totalCounter[i] += spek[i][j]
    # totalCounter[i] += length * partCounter[i] - totalCounter[i]
    # print(length * partCounter[i] - totalCounter[i])

# print(totalCounter)

spekSum = 0
# Данные по всем эталонным текстам
trainSpek = [0] * devi
trainTotal = 0
# Склеиваем
for i in range(len(spek)):
    if allText[i] not in trainText:
        continue
    for j in range(devi):
        trainSpek[j] += spek[i][j] #  * (j + 1)
    trainTotal += totalCounter[i]
    trainParts += partCounter[i]
# print(trainTotal, 'Train', trainSpek)
sum = 0
for j in range(devi):
    tp.append(trainSpek[j] / trainTotal)
    sum += tp[j]
    tpn.append(sum)

for i in range(len(spek)):
    spekSum = 0
    # print(partCounter[i], spek[i])
    # print(wordCounter[i], totalCounter[i])
    p.append([])
    pn.append([])
    sum = 0
    for j in range(devi):
        p[i].append(spek[i][j] / totalCounter[i])
        sum += p[i][j]
        pn[i].append(sum)
    # print(i, 'TOTAL', totalCounter[i])
# print('tpn', tp)
# print('pn', p[1])
for i in range(len(spek)):
    d.append([])
    for j in range(devi):
        d[i].append(abs(tpn[j] - pn[i][j]))
    maxD[i] = max(d[i])
    ld13m[i] = maxD[i] * np.sqrt(trainTotal * totalCounter[i] / (trainTotal + totalCounter[i]))
#######################################################################################################################
# 14mod
spek = list()
partCounter = [0] * COUNT
wordCounter = [0] * COUNT
totalCounter = [0] * COUNT
devi = 10

for i in range(COUNT):
    text = list()
    counter = 0
    spek.append([0] * devi)

    with open(AUTHOR + '_csv/' + str(allText[i]) + '.csv', encoding='UTF-8', newline='') as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                            quoting=csv.QUOTE_NONE)
        for row in reader:
            row[0] = row[0].replace('"', '').strip()
            row[1] = row[1].replace('"', '').strip()
            row[2] = row[2].replace('"', '').strip()
            if row[0] != "":
                counter += 1
                totalCounter[i] += 1
                text.append(row[1].lower())
            if counter == LENGTH:
                partCounter[i] += 1
                yet = list()
                for word in text:
                    if word in yet:
                        continue
                    yet.append(word)
                    col = text.count(word)
                    if col > devi:
                        col = devi
                    spek[i][col-1] += 1
                    wordCounter[i] += col
                counter = 0
                text.clear()
p = list()
pn = list()
d = list()
tp = list()
tpn = list()
mfSum = 0
maxD = [0] * len(spek)
ld14m = [0] * len(spek)

mf = list()
for i in range(len(spek)):
    mf.append([])
    mfSum = 0
    for j in range(devi - 1):
        mf[i].append(spek[i][j] * (j + 1))
        mfSum += spek[i][j] * (j + 1)
    mf[i].append(partCounter[i] * LENGTH - mfSum)
# print(mf[0])
# print(mf[1])

mfSum = 0
# Данные по всем эталонным текстам
trainSpek = [0] * devi
trainTotal = 0
# Склеиваем
for i in range(len(mf)):
    if allText[i] not in trainText:
        continue
    for j in range(devi):
        trainSpek[j] += mf[i][j] #  * (j + 1)
    trainTotal += partCounter[i] * LENGTH
# print(trainTotal, 'Train', trainSpek)
sum = 0
for j in range(devi):
    tp.append(trainSpek[j] / trainTotal)
    sum += tp[j]
    tpn.append(sum)
# print(tp)
# print(tpn)

for i in range(len(mf)):
    mfSum = 0
    # print(partCounter[i], mf[i])
    # print(wordCounter[i], totalCounter[i])
    totalCounter[i] = partCounter[i] * LENGTH
    p.append([])
    pn.append([])
    sum = 0
    for j in range(devi):
        p[i].append(mf[i][j] / totalCounter[i])
        sum += p[i][j]
        pn[i].append(sum)
    # print(totalCounter[i])
for i in range(len(mf)):
    d.append([])
    for j in range(devi):
        d[i].append(abs(tpn[j] - pn[i][j]))
    maxD[i] = max(d[i])
    ld14m[i] = maxD[i] * np.sqrt(trainTotal * totalCounter[i] / (trainTotal + totalCounter[i]))
    # print(d[i])
    # print(maxD[i], ld14[i])

#######################################################################################################################
# 15mod
res15m = list()

# Строки результатов
partlen = list()
partlen0 = list()
# Число строк результатов
nRow = 0

for i in range(COUNT):
    # Сам текст (словами)
    mass = list()
    with open(AUTHOR + '_csv/' + str(allText[i]) + '.csv', encoding='UTF-8', newline='') as File:
        reader = csv.reader(File, delimiter=',', quotechar=',',
                            quoting=csv.QUOTE_NONE)
        # Число слов в отрывке
        counter = 0
        for row in reader:
            row[0] = row[0].replace('"', '').strip()
            row[1] = row[1].replace('"', '').strip()
            row[2] = row[2].replace('"', '').strip()
            if row[0] != "":
                counter += 1
                if not row[1].lower() in mass:
                    mass.append(row[1].lower())

            if counter == LENGTH:
                if allText[i] in trainText:
                    partlen0.append(len(mass))
                # Номер текста - среднее значение на участке
                partlen.append([i, len(mass)])
                mass.clear()
                counter = 0
                nRow += 1

mean0 = np.mean(partlen0)
var0 = np.var(partlen0)
n0 = len(partlen0)
# print(partlen0)
# print('mean0, var0, n0')
# print(mean0, var0, n0)

for i in range(COUNT):
    partlen1 = list()
    for part in partlen:
        if i == part[0]:
            partlen1.append(part[1])
    mean1 = np.mean(partlen1)
    var1 = np.var(partlen1)
    n1 = len(partlen1)

    sd = np.sqrt(((n0 - 1) * var0 + (n1 - 1) * var1) / (n1 + n0 - 2))
    answer = ((mean1 - mean0) / sd * np.sqrt(n1 * n0 / (n0 + n1)))

    res15m.append([i, n1, mean1, var1, sd, answer])

# print(res15)

# Create a workbook and add a worksheet.
workbook = xlsxwriter.Workbook(xlsxNAME)
worksheet = workbook.add_worksheet()
trainFormat = workbook.add_format({
    'fg_color': 'green'
})
badFormat = workbook.add_format({
    'fg_color': 'red'
})
borderFormat = workbook.add_format({
    'fg_color': 'silver'
})
worksheet.write(0, 0, 'Код', borderFormat)
maxs = [0] * 18
for text in range(COUNT):
    worksheet.write(0, text + 1, text + 1, borderFormat)
    if allText[text] not in trainText:
        continue
    if abs(finalTable9[text + 2][8]) > abs(maxs[1]):
        maxs[1] = abs(finalTable9[text + 2][8])
    if abs(alpha10[text]) > abs(maxs[2]):
        maxs[2] = abs(alpha10[text])
    if abs(finalTable11[text + 2][8]) > abs(maxs[3]):
        maxs[3] = abs(finalTable11[text + 2][8])
    if abs(alpha12[text]) > abs(maxs[4]):
        maxs[4] = abs(alpha12[text])
    if abs(ld13[text]) > abs(maxs[5]):
        maxs[5] = abs(ld13[text])
    if abs(ld14[text]) > abs(maxs[6]):
        maxs[6] = abs(ld14[text])
    if abs(res15[text][5]) > abs(maxs[7]):
        maxs[7] = abs(res15[text][5])
    if abs(ld13m[text]) > abs(maxs[8]):
        maxs[8] = abs(ld13m[text])
    if abs(ld14m[text]) > abs(maxs[9]):
        maxs[9] = abs(ld14m[text])
    if abs(res15m[text][5]) > abs(maxs[10]):
        maxs[10] = abs(res15m[text][5])


for xlRow in range(COUNT):
    if allText[xlRow] in trainText:
        worksheet.write(xlRow + 1, 0, allText[xlRow], trainFormat)
        worksheet.write(xlRow + 1, 1, finalTable9[xlRow + 2][8], trainFormat)
        worksheet.write(xlRow + 1, 2, alpha10[xlRow], trainFormat)
        worksheet.write(xlRow + 1, 3, finalTable11[xlRow + 2][8], trainFormat)
        worksheet.write(xlRow + 1, 4, alpha12[xlRow], trainFormat)
        worksheet.write(xlRow + 1, 5, ld13[xlRow], trainFormat)
        worksheet.write(xlRow + 1, 6, ld14[xlRow], trainFormat)
        worksheet.write(xlRow + 1, 7, res15[xlRow][5], trainFormat)
        worksheet.write(xlRow + 1, 8, ld13m[xlRow], trainFormat)
        worksheet.write(xlRow + 1, 9, ld14m[xlRow], trainFormat)
        worksheet.write(xlRow + 1, 10, res15m[xlRow][5], trainFormat)
        strName = str(name[xlRow]).strip('[]')
        worksheet.write(xlRow + 1, 11, strName.replace(',', '').replace('\'', ''), trainFormat)
        continue

    worksheet.write(xlRow + 1, 0, allText[xlRow])

    if abs(finalTable9[xlRow+2][8]) > maxs[8]:
        worksheet.write(xlRow + 1, 1, finalTable9[xlRow + 2][8], badFormat)
    else:
        worksheet.write(xlRow + 1, 1, finalTable9[xlRow + 2][8])
    if abs(alpha10[xlRow]) > maxs[9]:
        worksheet.write(xlRow + 1, 2, alpha10[xlRow], badFormat)
    else:
        worksheet.write(xlRow + 1, 2, alpha10[xlRow])
    if abs(finalTable11[xlRow+2][8]) > maxs[10]:
        worksheet.write(xlRow + 1, 3, finalTable11[xlRow+2][8], badFormat)
    else:
        worksheet.write(xlRow + 1, 3, finalTable11[xlRow + 2][8])
    if abs(alpha12[xlRow]) > maxs[11]:
        worksheet.write(xlRow + 1, 4, alpha12[xlRow], badFormat)
    else:
        worksheet.write(xlRow + 1, 4, alpha12[xlRow])
    if abs(ld13[xlRow]) > maxs[12]:
        worksheet.write(xlRow + 1, 5, ld13[xlRow], badFormat)
    else:
        worksheet.write(xlRow + 1, 5, ld13[xlRow])
    if abs(ld14[xlRow]) > maxs[13]:
        worksheet.write(xlRow + 1, 6, ld14[xlRow], badFormat)
    else:
        worksheet.write(xlRow + 1, 6, ld14[xlRow])
    if abs(res15[xlRow][5]) > maxs[14]:
        worksheet.write(xlRow + 1, 7, res15[xlRow][5], badFormat)
    else:
        worksheet.write(xlRow + 1, 7, res15[xlRow][5])
    if abs(ld13m[xlRow]) > maxs[15]:
        worksheet.write(xlRow + 1, 8, ld13m[xlRow], badFormat)
    else:
        worksheet.write(xlRow + 1, 8, ld13m[xlRow])
    if abs(ld14m[xlRow]) > maxs[16]:
        worksheet.write(xlRow + 1, 9, ld14m[xlRow], badFormat)
    else:
        worksheet.write(xlRow + 1, 9, ld14m[xlRow])
    if abs(res15m[xlRow][5]) > maxs[17]:
        worksheet.write(xlRow + 1, 10, res15m[xlRow][5], badFormat)
    else:
        worksheet.write(xlRow + 1, 10, res15m[xlRow][5])

    strName = str(name[xlRow]).strip('[]')
    worksheet.write(xlRow + 1, 11, strName.replace(',', '').replace('\'', ''))

workbook.close()
