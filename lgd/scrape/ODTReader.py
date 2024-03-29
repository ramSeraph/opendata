# originally from https://github.com/marcoconti83/read-ods-with-odfpy
# Copyright 2011 Marco Conti
# Copyright 2022 ramSeraph - changed to read ODT Files( specifically those released by LGD )

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Thanks to grt for the fixes


import odf.opendocument
from odf.table import Table, TableRow, TableCell
from odf.text import P

# http://stackoverflow.com/a/4544699/1846474
class GrowingList(list):
    def __setitem__(self, index, value):
        if index >= len(self):
            self.extend([None]*(index + 1 - len(self)))
        list.__setitem__(self, index, value)


class ODTTableReader:
    # loads the file
    def __init__(self, file, clonespannedcolumns=None):
        self.clonespannedcolumns = clonespannedcolumns
        self.doc = odf.opendocument.load(file)
        start_node = self.doc.text
        self.SHEETS = []
        for sheet in start_node.getElementsByType(Table):
            if sheet.parentNode != start_node:
                continue
            self.readSheet(sheet)

    # reads a sheet in the sheet dictionary, storing each sheet as an
    # array (rows) of arrays (columns)
    def readSheet(self, sheet):
        #name = sheet.getAttribute("name")
        rows = sheet.getElementsByType(TableRow)
        arrRows = []

        # for each row
        for row in rows:
            if row.parentNode != sheet and row.parentNode.parentNode != sheet:
                continue
            row_comment = ""
            arrCells = GrowingList()
            cells = row.getElementsByType(TableCell)

            # for each cell
            count = 0
            for cell in cells:
                if cell.parentNode != row and cell.parentNode.parentNode != row:
                    continue
                # repeated value?
                repeat = cell.getAttribute("numbercolumnsrepeated")
                if not repeat:
                    repeat = 1
                    spanned = int(cell.getAttribute('numbercolumnsspanned') or 0)
                    # clone spanned cells
                    if self.clonespannedcolumns is not None and spanned > 1:
                        repeat = spanned

                ps = cell.getElementsByType(P)
                textContent = ""

                # for each text/text:span node
                for p in ps:
                    for n in p.childNodes:
                        if (n.nodeType == 1 and n.tagName == "text:span"):
                            for c in n.childNodes:
                                #print('{}/{} c: type: {}, {}'.format(rowid, cellid, c.nodeType, c.tagName))
                                if (c.nodeType == 3):
                                    textContent = u'{}{}'.format(textContent, c.data)

                        if (n.nodeType == 3):
                            textContent = u'{}{}'.format(textContent, n.data)

                if(textContent):
                    if(textContent[0] != "#"):  # ignore comments cells
                        for rr in range(int(repeat)):  # repeated?
                            arrCells[count]=textContent
                            count+=1
                    else:
                        row_comment = row_comment + textContent + " "
                else:
                    for rr in range(int(repeat)):
                        count+=1

            # if row contained something
            if(len(arrCells)):
                arrRows.append(arrCells)

            #else:
            #    print ("Empty or commented row (", row_comment, ")")

        self.SHEETS.append(arrRows)

    # returns a sheet as an array (rows) of arrays (columns)
    def getSheet(self, name):
        return self.SHEETS[name]


