''' Plugin for CudaText editor
Authors:
    Andrey Kvichansky    (kvichans on github.com)
Version:
    '0.8.0 2016-05-27'
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

NOT_IND = -1
class Command:
    class Sess:
        def __str__(self):
            return '' \
            +   f('row={}, (bgn,crt)={}, sel={}', self.row, (self.bgn_sub, self.crt_pos), self.sel_sub) \
            +   f(', i={}, bids={}',self.bids_i, (list(zip(self.bids, self.bids_c))))
        def __init__(self):
            self.row        = -1    # row for work
            self.crt_pos    = -1    # pos of caret (changed after substitution)
            self.bgn_sub    = -1    # Start pos to replace
            self.sel_sub    = False
            self.bids       = []
            self.bids_c     = []
            self.bids_i     = NOT_IND

    def dlg_config(self):
        DLG_W,  \
        DLG_H   = 380, 185
        minl_h  = _('Mininal characters to start completions (min=3)')
        incs_h  = _('What characters will be included to completion')
        itms    = [_('Word character'), _('Word chars and common signs'), _('All not spaces')]
        cnts    =[dict(           tp='lb'   ,tid='minl' ,l=GAP          ,w=160          ,cap=_('&Minimal base length:')  ,hint=minl_h           ) # &m
                 ,dict(cid='minl',tp='sp-ed',t=GAP      ,l=160          ,w=DLG_W-160-GAP                        ,props='3,10,1'                 ) #  
                 ,dict(cid='pair',tp='ch'   ,t=GAP+30   ,l=GAP          ,w=290          ,cap=_('&Expand variant to include good pair-character')) # &e
                 ,dict(           tp='lb'   ,tid='incs' ,l=GAP          ,w=130          ,cap=_('Find in &characters:')   ,hint=incs_h           ) # &c
                 ,dict(cid='incs',tp='cb-ro',t=GAP+60   ,l=160          ,w=DLG_W-160-GAP,items=itms                                             ) #
                 ,dict(           tp='lb'   ,tid='sgns' ,l=GAP          ,w=160          ,cap=_('Common si&gns:')                                ) # &g
                 ,dict(cid='sgns',tp='ed'   ,t=GAP+90   ,l=160          ,w=DLG_W-160-GAP                                                        ) #  
                 ,dict(cid='sngl',tp='ch'   ,t=GAP+120  ,l=GAP          ,w=290          ,cap=_('Do &not show list with single variant')         ) # &s
#                ,dict(cid='help',tp='bt'   ,t=DLG_H-60 ,l=DLG_W-GAP-80 ,w=80           ,cap=_('Help')                                          ) #  
                 ,dict(cid='!'   ,tp='bt'   ,t=DLG_H-30 ,l=DLG_W-GAP-165,w=80           ,cap=_('Save')          ,props='1'                      ) #     default
                 ,dict(cid='-'   ,tp='bt'   ,t=DLG_H-30 ,l=DLG_W-GAP-80 ,w=80           ,cap=_('Close')                                         ) #  
                ]#NOTE: cfg
        focused = 'minl'
#       while True:
        act_cid, vals, chds = dlg_wrapper(_('Configure in-text completions'), DLG_W, DLG_H, cnts
            , dict(minl=self.min_len
                  ,pair=self.pair_b
                  ,incs=apx.icase('|n-sp|' in self.cmpl , 2
                                 ,'|sgns|' in self.cmpl , 1
                                 ,True                  , 0)
                  ,sgns=self.sgns_s
                  ,sngl=self.sngl
                  ), focus_cid=focused)
        if act_cid is None or act_cid=='-':    return#while True
        focused = chds[0] if 1==len(chds) else focused
        if act_cid=='!':
            if vals['minl']!=self.min_len:
                apx.set_opt('itc_min_len', max(3, vals['minl']))
            if vals['pair']!=self.pair_b:
                apx.set_opt('itc_find_pair', vals['pair'])
            if vals['incs']!=apx.icase('|n-sp|' in self.cmpl, 2
                                      ,'|sgns|' in self.cmpl, 1
                                      ,True                 , 0):
                apx.set_opt('itc_find_within', apx.icase(vals['incs']==0, '|word|'
                                                        ,vals['incs']==1, '|sgns|'
                                                        ,vals['incs']==2, '|n-sp|'))
            if vals['sgns']!=self.sgns_s:
                apx.set_opt('itc_signs', vals['sgns'])
            if vals['sngl']!=self.sngl:
                apx.set_opt('itc_sngl', vals['sngl'])
            self._prep_const()
#               break#while
#          #while
       #def dlg_config

    def __init__(self):#NOTE: init
        self._prep_const()
        self.sess   = None          # Info to work "in one place" - try complete-bids
    def _prep_const(self):
        self.min_len= apx.get_opt('itc_min_len', 3)
        self.sngl   = apx.get_opt('itc_sngl', True)
        self.pair_b = apx.get_opt('itc_find_pair', True)
        brckts      = apx.get_opt('itc_brackets', '[](){}<>')
        self.quotes = apx.get_opt('itc_quotes', '"'+"'")
        self.opn2cls= {brckts[i  ]:brckts[i+1] for i in range(0,len(brckts),2)}
#       self.cls2opn= {self.brckts[i+1]:self.brckts[i  ] for i in range(0,len(self.brckts),2)}
        self.cmpl   = apx.get_opt('itc_find_within', '|n-sp|word|signs|')  # '|word|signs|n-sp|'
        self.sgns_s = apx.get_opt('itc_signs', r'!@#$%^&*-=+;:\|,./?`~"'+"'") # "'
        self.wrdc_s = apx.get_opt('word_chars', '') + '_'
        self.cmpl_s = r'\S+' \
                        if '|n-sp|' in self.cmpl else \
                      r'[\w'+re.escape(self.wrdc_s + self.sgns_s)+']+' \
                        if '|sgns|' in self.cmpl else \
                      r'[\w'+re.escape(self.wrdc_s)+']+' 
        self.base_re= re.compile(r'^[\w'+re.escape(self.wrdc_s)+']+')

    def set_next(self): return self._subst('next')
    def set_prev(self): return self._subst('prev')
    
    def _prep_sess(self):
        crts    = ed.get_carets()
        if len(crts)>1: 
            return app.msg_status(_("Command doesn't work with multi-carets"))
        (cCrt, rCrt
        ,cEnd, rEnd)= crts[0]
        if -1!=rEnd and rCrt!=rEnd:
            return app.msg_status(_("Command doesn't works with multi-line selection"))
        
        cEnd, rEnd  = (cCrt, rCrt) if -1==rEnd else (cEnd, rEnd)
        ((rSelB, cSelB)
        ,(rSelE, cSelE))= apx.minmax((rCrt, cCrt), (rEnd, cEnd))
        if        self.sess             \
        and  rCrt ==self.sess.row       \
        and (cSelB==self.sess.bgn_sub   \
            or not  self.sess.sel_sub)  \
        and  cSelE==self.sess.crt_pos:  # Not 1st call and Caret/Sel doesnot move/change
            return True                 # Sess OK
        
        what    = ''                    # Str to find
        wbnd    = True                  # Need left word bound
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
            and ch_aft.isspace()            \
            and (tx_bfr[-1].isalnum() 
              or tx_bfr[-1] in self.wrdc_s):
                tx_bfr_r= ''.join(reversed(tx_bfr))
                wrd_l   = len(self.base_re.search(tx_bfr_r).group())
                what    = line[cCrt-wrd_l:cCrt]
        if not  what \
        or not  what.strip():
            return app.msg_status(_('No data for search'))
        if len(what) < self.min_len:
            return app.msg_status(f(_('Need |base| >= {}'), self.min_len))
        pass;                  #LOG and log('what,wbnd={}',(what,wbnd))
        
        # Make new Sess
        self.sess           = Command.Sess()
        self.sess.row       = rCrt
        self.sess.crt_pos   = cSelE
        self.sess.bgn_sub   = cSelE - len(what)
        self.sess.sel_sub   = bool(sel)
        what_re = re.compile(''
                + (r'\b' if wbnd else '')
                + re.escape(what)
                + self.cmpl_s)
#               +  r'[\w'+re.escape(self.wrdc_s)+']+')
        pass;                  #LOG and log('what_re={}',(what_re.pattern))
        bids_d  = OrdDict()
        for line_n in range(ed.get_line_count()):
            if line_n == self.sess.row: continue#for line_n
            line    = ed.get_text_line(line_n)
            if self.pair_b:
                # Find+expand upto close brackets
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
        pass;                  #LOG and log('bids={}',(list(zip(self.sess.bids, self.sess.bids_c))))
        pass;                  #LOG and log('sess={}',(self.sess))
        pass;                  #return False
        return True
       #def _prep_sess
       
    def _subst(self, how):
        if not self._prep_sess(): return
        if not self.sess.bids:
            return app.msg_status(_('No in-text completions'))
        shft                = 1 if how=='next' else -1
        self.sess.bids_i    = 0 \
                                if self.sess.bids_i==NOT_IND else       \
                              (self.sess.bids_i+shft) % len(self.sess.bids)
        sub_s   = self.sess.bids[self.sess.bids_i]
        pass;                  #LOG and log('i, sub_s={}',(self.sess.bids_i, sub_s))
        ed.set_caret(self.sess.bgn_sub, self.sess.row)
        ed.delete(self.sess.bgn_sub, self.sess.row
                 ,self.sess.crt_pos, self.sess.row)
        ed.insert(self.sess.bgn_sub, self.sess.row
                 ,sub_s)
        self.sess.crt_pos   = self.sess.bgn_sub + len(sub_s)
        ed.set_caret(self.sess.crt_pos, self.sess.row, self.sess.bgn_sub, self.sess.row) \
            if self.sess.sel_sub else \
        ed.set_caret(self.sess.crt_pos, self.sess.row)
        next_i      = (self.sess.bids_i+shft) % len(self.sess.bids)
        next_info   = '' if 1==len(self.sess.bids) else \
                      f(_('. Next #{}: "{}"'), next_i, self.sess.bids[next_i][:50])
        app.msg_status(f(_('In-text completion #{} ({}){}'), 1+self.sess.bids_i, len(self.sess.bids), next_info))
       #def _subst
        
    def show_list(self):
        if not self._prep_sess(): return
        if not self.sess.bids:
            return app.msg_status(_('No in-text completions'))
#       exps    = ['qwerty', 'qazwsx']
        if self.sngl and 1==len(self.sess.bids):
            return self._subst('next')
        ed.complete('\n'.join(self.sess.bids), self.sess.crt_pos-self.sess.bgn_sub, 0)
        
   #class Command

'''
ToDo
[+][kv-kv][27may16] Start
[ ][kv-kv][27may16] 
'''
