# -*- coding: utf-8 -*-

import os
import sys


class ExtensionMapperReassembler:

  REBUILT_HEADER = "// This file was post-reassembled"
  EXTENSION_MAPPER_FILENAME = 'ExtensionMapper.java'

  def parse(self, extension_mapper_path):
    if not os.path.exists(extension_mapper_path):
      raise Exception("There is no ExtensionMapper.java in %s" % extension_mapper_path)

    with open(extension_mapper_path, 'r') as f:
      first_line = f.readline()
      if ExtensionMapperReassembler.REBUILT_HEADER in first_line:
        raise Exception("This file is already post-assembled.")

    self.header = []
    self.method_header = []
    self.footer = []
    self.contents = []

    stage = 'header'    # header, methodHeader, contents, footer

    for line in open(extension_mapper_path, 'r'):
      stripped = line.strip()
      nextStage = self.determineStage(stripped)
      stage = nextStage if nextStage else stage
      self.handleStage(stage, stripped)

  def determineStage(self, line):
    if line.startswith('if'):
      self.contents.append([])
      return 'contents'
    elif line.startswith("throw new org.apache.axis2.databinding.ADBException"):  # throw statement.
      return 'footer'
    elif line.startswith('public static java.lang.Object getTypeObject'):
      return 'methodHeader'
    else:
      return None

  def handleStage(self, stage, line):
    if stage == 'header':
      self.header.append(line)
    elif stage == 'methodHeader':
      self.method_header.append(line)
    elif stage == 'footer':
      self.footer.append(line)
    elif stage == 'contents':
      if line:
        self.contents[-1].append(line)
      # append to the last content
    else:
      raise Exception("stage %s is not supported." % stage)

  def createNamespaceMap(self):
    namespaceMap = {}
    for if_block in self.contents:
      namespace = if_block.pop(1).strip().strip("&&")
      if namespace not in namespaceMap:
        namespaceMap[namespace] = []
      namespaceMap[namespace].append(if_block)
    return namespaceMap

  def reassemble(self, extension_mapper_path):
    self.parse(extension_mapper_path)
    namespaceMap = self.createNamespaceMap()
    ret = [ExtensionMapperReassembler.REBUILT_HEADER]
    method_idx = 0
    ret.extend(self.header)
    for condition, if_blocks in namespaceMap.iteritems():
      ret.append(''.join(self.method_header).replace(
        'getTypeObject(java.lang.String namespaceURI,', 'getTypeObject%d(' % method_idx))
      ret.extend([''.join(if_block) for if_block in if_blocks])
      ret.append(
        'throw new org.apache.axis2.databinding.ADBException("Unsupported type " + typeName);')
      ret.append('}')
      method_idx += 1

    method_idx = 0
    ret.extend(self.method_header)
    for condition, if_blocks in namespaceMap.iteritems():
      ret.append('if (%s) {' % condition)
      ret.append('getTypeObject%d(typeName, reader);' % method_idx)
      ret.append('}')
      method_idx += 1

    ret.extend(self.footer)
    return ret

  @staticmethod
  def findExtensionMapperFile(wsdl_buildpath):
    for (path, fileDir, files) in os.walk(wsdl_buildpath):
      for filename in files:
        if filename == ExtensionMapperReassembler.EXTENSION_MAPPER_FILENAME:
          return os.path.join(path, filename)
    raise Exception("There is no %s in %s" % (
      ExtensionMapperReassembler.EXTENSION_MAPPER_FILENAME, wsdl_buildpath))


if __name__ == '__main__':
  if len(sys.argv) < 2:
    print "Usage: %s [source folder]"
    sys.exit(0)
  reassembler = ExtensionMapperReassembler()
  extension_mapper_path = ExtensionMapperReassembler.findExtensionMapperFile(sys.argv[1])
  print("ExtensionMapper.java location: %s" % extension_mapper_path)
  ret = reassembler.reassemble(extension_mapper_path)
  f = open(extension_mapper_path, 'w')
  f.write('\n'.join(ret))
