''' Plugin for CudaText editor
Authors:
    Andrey Kvichansky    (kvichans on github.com)
Version:
    '0.9.0 2016-06-06'
ToDo: (see end of file)
'''

import  re, os, sys, glob, json, collections
from    fnmatch         import fnmatch
import  cudatext            as app
from    cudatext        import ed
import  cudatext_cmd        as cmds
import  cudax_lib           as apx
from    .cd_plug_lib    import *

OrdDict = collections.OrderedDict
#FROM_API_VERSION= '1.0.119'

pass;                           LOG = (-2==-2)  # Do or dont logging.
pass;                           from pprint import pformat
pass;                           pf=lambda d:pformat(d,width=150)

_   = get_translation(__file__) # I18N

c10 = chr(10)
c13 = chr(13)
NOT_IND = -1
class Command:
    class Sess:
        def __str__(self):
            return '' \
            +   f('we={}, row={}, (bgn,crt)={}, sel={}', self.wdex, self.row, (self.bgn_sub, self.crt_pos), self.sel_sub) \
            +   f(', i={}, bids={}',self.bids_i, (list(zip(self.bids, self.bids_rs))))
        def __init__(self):
            self.wdex       = ''        # type: 'word' or 'expr'
            self.row        = -1        # row for work
            self.crt_pos    = -1        # pos of caret (changed after substitution)
            self.bgn_sub    = -1        # Start pos to replace
            self.sel_sub    = False     # Select after subst
            self.bids       = []        # Variants
            self.bids_rs    = []        # Source row inds
            self.bids_i     = NOT_IND   # Last used index of bids

    def dlg_config(self):
        DLG_W,  \
        DLG_H   = 430, 300
        minl_h  = _('Mininal characters in selection or previous string to start completion')
        incs_h  = _('What characters will be included to completion variant.'
                    '\rLetters and digits always are included.')
        pair_c  = _('&Expands to include both pair-characters')
        pair_h  = _('Example: "·" is space.'
                    '\rVariants for "fun":'
                    '\r   function'
                    '\r   fun="a·b"'
                    '\r   fun(·1,·2·)'
                    '\r   fun(·1,·m()·)'
                    )
        sngl_c  = _('Do&nt show list with single variant. Directly use the variant.')
        cnts    =[dict(           tp='lb'   ,t=5        ,l=5        ,w=130        ,cap=_('Word-like variant:')                          ) #
                 ,dict(           tp='lb'   ,tid='wdcs' ,l=40       ,w=130        ,cap=_('Contains extra si&gns:')          ,hint=incs_h) # &g
                 ,dict(cid='wdcs',tp='ed'   ,t=25       ,l=180      ,w=DLG_W-180-5                                                      ) #

                 ,dict(           tp='lb'   ,t=65       ,l=5        ,w=130        ,cap=_('Expession-like variant:')                     ) #
                 ,dict(           tp='lb'   ,tid='excs' ,l=40       ,w=130        ,cap=_('Contains extra &signs:')          ,hint=incs_h) # &s
                 ,dict(cid='excs',tp='ed'   ,t=85       ,l=180      ,w=DLG_W-180-5                                                      ) #
                 ,dict(cid='exal',tp='ch'   ,t=110      ,l=180      ,w=130        ,cap=_('An&y not spaces')         ,_act=1             ) # &y
                 ,dict(cid='pair',tp='ch'   ,t=135      ,l=40       ,w=290        ,cap=pair_c                               ,hint=pair_h) # &e

                 ,dict(           tp='lb'   ,tid='minl' ,l=5        ,w=180        ,cap=_('&Minimal base length (2-5):')     ,hint=minl_h) # &m
                 ,dict(cid='minl',tp='sp-ed',t=180      ,l=180      ,w=DLG_W-180-5                                  ,props='2,5,1'      ) #  
                 ,dict(cid='near',tp='ch'   ,t=210      ,l=5        ,w=290        ,cap=_('Start with variant from nea&rest line.')      ) # &r
                 ,dict(cid='sngl',tp='ch'   ,t=240      ,l=5        ,w=290        ,cap=sngl_c                                           ) # &n
                 ,dict(cid='!'   ,tp='bt'   ,t=DLG_H-30 ,l=DLG_W-180,w=80         ,cap=_('Save')                    ,props='1'          ) #    default
                 ,dict(cid='-'   ,tp='bt'   ,t=DLG_H-30 ,l=DLG_W-85 ,w=80         ,cap=_('Cancel')                                      ) #  
                ]#NOTE: cfg
        vals    = dict(minl=self.min_len
                      ,near=self.near
                      ,sngl=self.sngl
                      ,wdcs=self.wdsgns
                      ,excs=self.exsgns
                      ,exal=self.exall
                      ,pair=self.expair
                      )
        focused = 'wdcs'
        if True:#while True:
            act_cid, vals, chds = dlg_wrapper(_('Configure in-text completions'), DLG_W, DLG_H, cnts, vals, focus_cid=focused)
            if act_cid is None or act_cid=='-':    return#while True
            focused = chds[0] if 1==len(chds) else focused
            if act_cid=='!':
                if vals['minl']!=self.min_len:
                    apx.set_opt('itc_min_len', max(2, vals['minl']))
                if vals['sngl']!=self.sngl:
                    apx.set_opt('itc_sngl', vals['sngl'])
                if vals['near']!=self.near:
                    apx.set_opt('itc_near', vals['near'])
                
                if vals['wdcs']!=self.wdsgns:
                    apx.set_opt('itc_word_signs', vals['wdcs'])
                
                if vals['excs']!=self.exsgns:
                    apx.set_opt('itc_expr_signs', vals['excs'])
                if vals['exal']!=self.exall:
                    apx.set_opt('itc_expr_all',   vals['exal'])
                if vals['pair']!=self.expair:
                    apx.set_opt('itc_expr_pair',  vals['pair'])
                
                self._prep_const()
#               break#while
           #while
       #def dlg_config

    def __init__(self):#NOTE: init
        self._prep_const()
        self.sess   = None          # Info to work "in one place" - try complete-bids
    
    def _prep_const(self):
        brckts      = apx.get_opt('itc_brackets', '[](){}<>')

        self.min_len= apx.get_opt('itc_min_len', 3)
        self.sngl   = apx.get_opt('itc_sngl', True)
        self.near   = apx.get_opt('itc_near', True)
        
        self.wdsgns = apx.get_opt('itc_word_signs', '_')
        
        self.exsgns = apx.get_opt('itc_expr_signs', r'!@#$%^&*-_=+;:\|,./?`~"'+"'"+brckts) # "'
        self.exall  = apx.get_opt('itc_expr_all', True)
        self.expair = apx.get_opt('itc_expr_pair', True)
        
        self.quotes = apx.get_opt('itc_quotes', '"'+"'")
        self.opn2cls= {brckts[i  ]:brckts[i+1] for i in range(0,len(brckts),2)}
        self.cls2opn= {brckts[i+1]:brckts[i  ] for i in range(0,len(brckts),2)}
#       self.cmpl   = apx.get_opt('itc_find_within', '|n-sp|word|signs|')  # '|word|signs|n-sp|'
        
        self.wdcmpl = r'[\w'+re.escape(self.wdsgns)+']+' 
        self.excmpl = r'\S+' \
                        if self.exall else \
                      r'[\w'+re.escape(self.exsgns)+']+'
        
        self.base_re= re.compile(self.wdcmpl)

    def _prep_sess(self, wdex='word'):
        """ Params
                wdex    Type of sess
                            'word' / 'expr'
        """
        crts    = ed.get_carets()
        if len(crts)>1: 
            return app.msg_status(_("Command doesn't work with multi-carets"))
        (cCrt, rCrt
        ,cEnd, rEnd)= crts[0]
        if -1!=rEnd and rCrt!=rEnd:
            return app.msg_status(_("Command doesn't work with multi-line selection"))
        
        cEnd, rEnd  = (cCrt, rCrt) if -1==rEnd else (cEnd, rEnd)
        ((rSelB, cSelB)
        ,(rSelE, cSelE))= apx.minmax((rCrt, cCrt), (rEnd, cEnd))
        stayed      =           self.sess           \
                    and  rCrt ==self.sess.row       \
                    and (cSelB==self.sess.bgn_sub   \
                        or not  self.sess.sel_sub)  \
                    and  cSelE==self.sess.crt_pos   # Not 1st call and Caret/Sel doesnot move/change
        if stayed   and   wdex==self.sess.wdex:
            # Sess OK
            return True

        what        = ''                    # Str to find
        wbnd        = True                  # Need left word bound
        sel         = ''
        if stayed   and   wdex!=self.sess.wdex:
            # Change sess type
            what    = self.sess.src_what
            wbnd    = self.sess.src_wbnd
        if not stayed:
            # New sess
            line    = ed.get_text_line(rCrt)
            sel     = ed.get_text_sel()
            if sel:
                # Use selection to find
                what    = sel
                wbnd    = 0==cSelB or line[cSelB-1].isspace()
            else:
                # Use "chars around caret" to find 
                tx_bfr  = line[:cCrt]
                ch_aft  = line[cCrt] if cCrt<len(line) else ' '
                pass;              #LOG and log('ch_aft,tx_bfr={}',(ch_aft,tx_bfr))
                if  len(tx_bfr)>=self.min_len   \
                and (ch_aft.isspace() or True or ch_aft in self.cls2opn) \
                and (tx_bfr[-1].isalnum() 
                  or tx_bfr[-1] in self.wdsgns):
                    tx_bfr_r= ''.join(reversed(tx_bfr))
                    wrd_l   = len(self.base_re.match(tx_bfr_r).group())
                    what    = line[cCrt-wrd_l:cCrt]
        
        if not  what \
        or not  what.strip():
            return app.msg_status(_('No data for search'))
        if len(what) < self.min_len:
            return app.msg_status(f(_('Need |base| >= {}'), self.min_len))
        pass;                  #LOG and log('what,wbnd={}',(what,wbnd))
        
        asword              = wdex=='word'
        asexpr              = wdex=='expr'
        # Make new Sess
        if not stayed:
            self.sess           = Command.Sess()
            self.sess.row       = rCrt
            self.sess.crt_pos   = cSelE
            self.sess.bgn_sub   = cSelE - len(what)
            self.sess.sel_sub   = bool(sel)
            self.sess.src_what  = what
            self.sess.src_wbnd  = wbnd
        self.sess.wdex          = wdex
        what_re = re.compile(''
                            + (r'\b' if wbnd else '')
                            + re.escape(what)
                            + (self.wdcmpl if asword else self.excmpl)
                            )
#               +  r'[\w'+re.escape(self.wdsgns)+']+')
        pass;                  #LOG and log('what_re={}',(what_re.pattern))
        bids_d  = OrdDict()
        for line_n in range(ed.get_line_count()):
            if line_n == self.sess.row: continue#for line_n
            line    = ed.get_text_line(line_n)
            if asexpr and self.expair:
                # Find+expand upto close brackets/quotes
                lbids_l = []
                for m in what_re.finditer(line):
                    lbid    = m.group(0)
                    
                    ok      = False
                    for op, cl in self.opn2cls.items():
                        if  op in lbid and  lbid.count(op)      > lbid.count(cl):   # Try expand to good cl
                            ext_bgn = m.end()
                            ext_end = line.find(cl, ext_bgn)
                            while -1!=ext_end:
                                lbid_ext    = lbid + line[ext_bgn:ext_end+1]
                                if          lbid_ext.count(op) == lbid_ext.count(cl):
                                    lbid,ok = lbid_ext, True
                                    break#while
                                ext_end = line.find(cl, ext_end+1)
                        if ok: break#for op
                       #for op
                    ok      = False
                    for qu in self.quotes:
                        if  qu in lbid and  1 == lbid.count(qu)     % 2:            # Try expand to good qu
                            ext_bgn = m.end()
                            ext_end = line.find(qu, ext_bgn)
                            while -1!=ext_end:
                                lbid_ext    = lbid + line[ext_bgn:ext_end+1]
                                if          0 == lbid_ext.count(qu) % 2:
                                    lbid,ok = lbid_ext, True
                                    break#while
                                ext_end = line.find(cl, ext_end+1)
                        if ok: break#for qu
                       #for qu
                    
                    lbids_l.append(lbid)
                   #for m
            else:
                # Find only
                lbids_l = what_re.findall(line)
            if lbids_l:
                bids_d.update({bid:line_n 
                                for bid in lbids_l 
                                if  bid not in bids_d
                                or  abs(line_n-self.sess.row)<abs(bids_d[bid]-self.sess.row)
                              })  # closest
        if not bids_d:
            return app.msg_status(_('No in-text completions'))
            
        self.sess.bids      = list(bids_d.keys())
        self.sess.bids_c    = list(bids_d.values())
        self.sess.bids_i    = NOT_IND
        if len(self.sess.bids)>1 and self.near:
            self.sess.bids_i= min([(abs(bid_r-self.sess.row), bid_i) 
                                    for (bid_i,bid_r) in enumerate(self.sess.bids_c)
                                  ])[1]
        pass;                  #LOG and log('bids={}',(list(zip(self.sess.bids, self.sess.bids_c))))
        pass;                  #LOG and log('sess={}',(self.sess))
        pass;                  #return False
        return True
       #def _prep_sess
       
    def _subst(self, which, wdex):
        """ Do completion.
            Params
                which   Which variant to use
                            'next' / 'prev' / '#N'
                wdex    What list to use
                            'word' / 'expr' / 'curr'
        """
        pass;                  #LOG and log('which, wdex={}',(which, wdex))
        if wdex!='curr' and \
           not self._prep_sess(wdex): return
        if not self.sess.bids:
            return app.msg_status(_('No in-text completions'))
        shft                = 1 if which=='next' else -1
        self.sess.bids_i    = int(which.strip('#')) \
                                if which[0]=='#' else \
                              0 \
                                if self.sess.bids_i==NOT_IND else \
                              (self.sess.bids_i+shft) % len(self.sess.bids)
        sub_s   = self.sess.bids[self.sess.bids_i]
        pass;                  #LOG and log('i, sub_s={}',(self.sess.bids_i, sub_s))
        ed.set_caret(self.sess.bgn_sub, self.sess.row)
        ed.delete(self.sess.bgn_sub, self.sess.row
                 ,self.sess.crt_pos, self.sess.row)
        ed.insert(self.sess.bgn_sub, self.sess.row
                 ,sub_s)
        self.sess.crt_pos   = self.sess.bgn_sub + len(sub_s)
        if self.sess.sel_sub:
            ed.set_caret(self.sess.crt_pos, self.sess.row
                        ,self.sess.bgn_sub, self.sess.row)
        else:
            ed.set_caret(self.sess.crt_pos, self.sess.row)
        next_i      = (self.sess.bids_i+shft) % len(self.sess.bids)
        next_info   = '' if 1==len(self.sess.bids) else \
                      f(_('. Next #{}: "{}"'), next_i, self.sess.bids[next_i][:50])
        app.msg_status(f(_('In-text completion #{} ({}){}'), 1+self.sess.bids_i, len(self.sess.bids), next_info))
       #def _subst
    def set_next_wd(self):  return self._subst('next', 'word')
    def set_next_ex(self):  return self._subst('next', 'expr')
    def set_prev_wd(self):  return self._subst('prev', 'word')
    def set_prev_ex(self):  return self._subst('prev', 'expr')

    def show_list_wd(self): return self.show_list('word')
    def show_list_ex(self): return self.show_list('expr')
    def show_list(self, wdex):
        if app.app_api_version()<'1.0.144': return app.msg_status(_('Need update CudaText'))
        if not self._prep_sess(wdex): return
        if not self.sess.bids:
            return app.msg_status(_('No in-text completions'))
        if self.sngl and 1==len(self.sess.bids):
            return self._subst('#0', 'curr')
        ed.complete_alt(c10.join([bd.replace(c9, '¬')
                                +c9+f(':{}', 1+self.sess.bids_c[ibd])
                                +c9+str(ibd) 
                                for (ibd, bd) in enumerate(self.sess.bids)])
                       ,'in-text_complete', 0
                       ,self.sess.bids_i)
       #def show_list
    def on_snippet(self, ed_self, snippet_id, snippet_text):
        pass;                  #LOG and log('snippet_id,snippet_text={}',(snippet_id,snippet_text))
        if snippet_id != 'in-text_complete':    return
        self._subst('#'+snippet_text, 'curr')
   #class Command

'''
ToDo
[+][kv-kv][27may16] Start
[ ][kv-kv][30may16] If [x]pair try to cut bid to balance
[?][kv-kv][30may16] Store opts in cuda_itc.json with short names?
[?][kv-kv][30may16] Store opts in user.json     with wider names?
[?][kv-kv][30may16] Save invertion for sel ?
[ ][kv-kv][30may16] Complete before close brackets
[ ][kv-kv][05jun16] Select nearest (by row) bid when show list before first substs
'''
