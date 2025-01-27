"""Make documentation
"""

import os
import sys
import re
import shutil
from typing import TypeVar, Union

SILENT=False
VERBOSE=False
WARNING=True

class Html:

    COMMENTS = False

    def __init__(self,filename):
        self.file = open(filename,"w")
        print("<!DOCTYPE html>",file=self.file)
        self.block = []

    def comment(self,text):
        if self.COMMENTS:
            print(f"\n  <!-- {text} -->\n",file=self.file)
        return

    def active(self,tag:str=None) -> Union[bool,str]:
        """Get currently active block

        Arguments:

        * `tag`: block tag to check

        Returns:

        * `bool`: active block matches tag (if tag is specified)

        * `str`: name of currently active block (if tag not specified)
        """
        if not tag:
            result = self.block[-1] if len(self.block) > 0 else None
        else:
            result = self.active() == tag
        self.comment(f"active(tag={repr(tag)}) => {result}")
        return result

    def data(self,text:str):
        """Output data

        Arguments:

        * `text`: text to output
        """
        self.comment(f"data(text={repr(text)})")
        print(text,end="",file=self.file)

    def open(self,tag:str,standalone:bool=False,data:str=None,**kwargs):
        """Open a new block

        Arguments:

        * `tag`: block tag

        * `standalone`: close block immediate without data

        * `data`: close block immediately with data (standalone must be `False`)

        * `**kwargs`: HTML arguments to tag
        """
        self.comment(f"open(tag={repr(tag)},standalone={repr(standalone)},data={repr(data)},**kwargs={repr(kwargs)})")
        if self.active() != tag:
            print(f"<{tag}{' ' if kwargs else ''}",end="",file=self.file)
            print(" ".join([f'{x}="{y}"' for x,y in kwargs.items() if y is not None]),end="",file=self.file)
            print(f"{'/' if standalone else ''}>",end="" if data else None,file=self.file)
        if not standalone:
            if data:
                print(f"{data}</{tag}>",file=self.file)
            elif self.active() != tag:
                self.block.append(tag)

    def close(self,back:[str,int]=1):
        """Close blocks

        Arguments:

        * `back`: blocks to close (None for all open blocks)

        Remarks:

        If `back` is an integer, the last `back` blocks are closed. If `back` is a 
        string, all blocks back to the `back` block name are closed.
        """
        self.comment(f"close(back={repr(back)})")
        if back is None:
            back = len(self.block)
        if isinstance(back,int):
            while back > 0:
                print(f"</{self.active()}>",file=self.file)
                del self.block[-1]
                back -= 1
        elif isinstance(back,str):
            while self.active() != back:
                print(f"</{self.block[-1]}>",file=self.file)
                del self.block[-1]
            self.close()
        else:
            raise TypeError("back must be int or str")

    def closeall(self,tags:list[str]=[],enabled:bool=True):
        """Close all blocks and files

        Arguments:

        * `tags`: list of tags to close (leaves file open), or None
          (closes everything)

        * `enabled`: secondary condition for closing tags in list
        """
        self.comment(f"closeall(tags={repr(tags)},enabled={repr(enabled)})")
        if not isinstance(tags,list):
            raise TypeError("tags must a list of strings")
        elif tags:
            while self.active() in tags and enabled:
                self.close()
        else:
            self.close(None)
            self.file.close()


class Markdown:

    def __init__(self,filename,basepath=None):

        try:
            self.lines = open(filename,"rt").readlines()
        except UnicodeDecodeError as err:
            e_type,e_value,e_trace = sys.exc_info()
            self.lines = [str(e_type.__name__),str(e_value)]
            error(f"{filename} ({e_type.__name__}) {e_value}")
        self.path,self.name = os.path.split(filename)
        self.base = basepath if basepath else self.path

    def inline(self,x:str) -> str:
        mappings = [
            [r"\*([^*]+)\*",r"<I>\1</I>"], # italic
            [r"\*\*([^*]+)\*\*",r"<B>\1</B>"], # bold
            [r"`([^`]+)`",r"<CODE>\1</CODE>"], # code
            [r"__([^_]+)__",r"<U>\1</U>"], # underline
            [r"\[([^]]+)\]\(([^)]+)\)",r'<A HREF="\2" TARGET="content">\1</A>'], # decorated link
            [r"\[\[/(.+)\]\]",r'<A HREF="\1.html" TARGET="content">/\1</A>'], # internal link
            [r"\(\(([^\)]+)\)\)",r'<A HREF="\1.html" TARGET="content"><INPUT TYPE="submit" CLASS="header" VALUE="\1"/></A>'],
            [r"\[image:([^]]*)\]",r'<IMG SRC="\1" ALT="\1" WIDTH="100%"/>'], # img
            [r"\[video:([^]]*)\]",r'<iframe width="560" height="315" src="https://www.youtube.com/embed/\1" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'], # img
            ]
        for mapping in mappings:
            # old = x
            x = re.sub(*mapping,x)
            # if "[image:" in old:
            #     print("\n\n-->",mapping,"\n")
            #     print(old)
            #     print(x)
        return x

    def to_html(self,filename,**kwargs):

        html = Html(filename)
        html.open("HTML")
        html.open("HEAD")
        html.open("BASE",HREF=self.base,standalone=True)
        html.close("HEAD")
        html.open("BODY")

        for line in self.lines:

            stripped = line.strip()

            # in preformatted text
            if html.active("PRE"):

                # only ~~~ will stop preformatting
                if stripped.startswith("~~~") and stripped == "~"*len(stripped):

                    html.close()

                else:

                    html.data(line)

            # paragraph
            elif not stripped and html.active() not in ["OL","UL","DL"]:

                html.open("P",standalone=True)

            # headings
            elif heading := re.match(r"^(#+)[ \t]",stripped):

                # close all lists
                html.closeall(["OL","UL","DL"],True if stripped else False)
                html.open(f"H{len(heading.group(1).strip())}",
                    data=self.inline(line[len(heading.group(1).strip()):]),
                    )

            # preformatted block
            elif stripped.startswith("~~~") and stripped == "~"*len(stripped):

                # start preformatted block
                html.open("PRE")

            # bullet
            elif item := re.match(r"^[*-][ \t]+(.+)",stripped):

                html.open("UL")
                html.open("LI",data=self.inline(item.group(1)))

            # numbered
            elif item := re.match(r"^[0-9]+\.[ \t]+(.+)",stripped):

                html.open("OL")
                html.open("LI",data=self.inline(item.group(1)))

            # definition
            elif item := re.match(r"^[*-][ \t]+(.+):[ \t]+(.+)",stripped):

                html.open("DL")
                html.open("DT",data=self.inline(item.group(1)))
                html.open("DD",data=self.inline(item.group(2)))

            else:

                # close all lists
                html.closeall(["OL","UL","DL"],True if stripped else False)
                html.data(self.inline(line))

        html.close("BODY")
        html.closeall()

class Sidebar:

    def __init__(self,target):

        self.fh = open(os.path.join(target,"_sidebar.html"),"w")
        self.target = target
        self.tree = []
        self.list = []

    def add(self,filename):
        href = filename.replace(self.target,"")
        if "/" in href:
            self.tree.append(href)
        elif not href.startswith("_"):
            self.list.append(href)

    def write(self,*args,**kwargs):
        print(*args,file=self.fh,**kwargs)

    def flush(self):
        verbose("Writing sidebar...")

        # folders
        folder = None
        for href in sorted(self.tree):
            path,name = os.path.split(href)
            path = path.split("/")
            name = os.path.splitext(name)[0]
            if path != folder:
                if not folder is None:
                    self.write("</UL>")
                n = len(path)
                self.write(f"<H{n}>{path[-1]}</H{n}><UL>")
                folder = path

            self.write(f'<LI><A HREF="{href}" TARGET="content">{name}</A></LI>')
        self.write("</UL>")

        # files      
        self.write("<UL>")
        for name in sorted(self.list):
            self.write(f'<LI><A HREF="{name}" TARGET="content">{os.path.splitext(name)[0]}</A></LI>')
        self.write("</UL>")
        self.fh.flush()

def error(msg):

    if not SILENT:
        print(f"ERROR [{os.path.basename(sys.argv[0])}]: {msg}",file=sys.stderr, flush=True)

def verbose(msg):

    if VERBOSE:
        print(f"VERBOSE [{os.path.basename(sys.argv[0])}]: {msg}",file=sys.stderr)

def warning(msg):

    if WARNING:
        print(f"WARNING [{os.path.basename(sys.argv[0])}]: {msg}",file=sys.stderr)

def main(source,target,base=None,sidebar=None):

    verbose(f"Processing {source} to {target}...")
    os.makedirs(target,exist_ok=True)
    if not base:
        base = target[:-1] if target.endswith("/") else target

    if not sidebar:
        verbose(f"Creating {os.path.join(target,'sidebar.html')}...")
        sidebar = Sidebar(target)

    for folders in [False,True]: # show folders first, then files

        for infile in os.listdir(source):

            inpath = os.path.dirname(infile)
            inname,inext = os.path.splitext(os.path.basename(infile))
            outpath = os.path.join(target,inpath)
            os.makedirs(outpath,exist_ok=True)
            outname = inname + ".html"
            outfile = os.path.join(outpath,outname)

            if folders:

                if os.path.isdir(os.path.join(source,infile)):
                    args = [os.path.join(x,infile) for x in [source,target]]
                    main(*args,base,sidebar)
            else:

                if infile.endswith(".md"):

                    verbose(f"Converting {os.path.join(source,infile)}...")

                    md = Markdown(os.path.join(source,infile),base)
                    md.to_html(outfile)
                    sidebar.add(outfile)


                elif os.path.splitext(infile)[1] in [".png"]:

                    verbose(f"Copying {os.path.join(source,infile)}...")
                    shutil.copy(os.path.join(source,infile),outpath)

                else:

                    verbose(f"Skipping {os.path.join(source,infile)}...")

    return [sidebar]

if __name__ == "__main__":

    if not sys.argv[0] or len(sys.argv) == 1:

        os.chdir("docs")
        sys.argv = ["mkdocs.py","../gridlabd/docs/","./",f"file://{os.getcwd()}/"]

    files = main(source=sys.argv[1],\
        target=sys.argv[2],
        base=sys.argv[3])
    for file in files:
        file.flush()