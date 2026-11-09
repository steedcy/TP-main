ss=q.steps();ss[2]['inputParams']['contentData']='F185超规行李办理说明：请凭临时业务号前往F2_TEST_GATE，核验重量与尺寸，按承运人现场政策办理托运并遵守安全须知。'
q.config('F185_UI_GOAL',steps=ss,goalOverride={'inferredTaskFamily':'OVERSIZE_BAGGAGE_HANDLING','infoComplete':True})
q.config('T2值机岛',steps=ss,goalOverride={'inferredTaskFamily':'OVERSIZE_BAGGAGE_HANDLING','infoComplete':True})
q.save();result={'prepared':True}
