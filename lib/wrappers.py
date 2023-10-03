import os
import numpy as np
import matplotlib.pyplot as plt
from obspy.core import Stream
import SDS
import FDSNtools
import InventoryTools
import IceWeb

def FDSN_to_SDS_daily_wrapper(startt, endt, SDS_TOP, centerlat=None, centerlon=None, searchRadiusDeg=None, trace_ids=None, \
        fdsnURL="http://service.iris.edu", overwrite=True, inv=None):
    '''
    Download Stream from FDSN server and save to SDS format. Default is to overwrite each time.
    
    NSLC combinations to download either come from (1) trace_ids name-value pair, (2) inv name-value pair, (3) circular search parameters, in that order.

        Parameters:
            startt (UTCDateTime): An ObsPy UTCDateTime marking the start date/time of the data request.
            endt (UTCDateTime)  : An ObsPy UTCDateTime marking the end date/time of the data request.
            SDS_TOP (str)       : The path to the SDS directory structure.

        Optional Name-Value Parameters:
            trace_ids (List)    : A list of N.S.L.C strings. Default None. If given, this overrides other options.
            inv (Inventory)     : An ObsPy Inventory object. Default None. If given, trace_ids will be extracted from it, unless explicity given.
            centerlat (float)   : Decimal degrees latitude for circular station search. Default None.
            centerlon (float)   : Decimal degrees longitude for circular station search. Default None.
            searchRadiusDeg (float) : Decimal degrees radius for circular station search. Default None.
            fdsnURL (str) : URL corresponding to FDSN server. Default is "http://service.iris.edu".
            overwrite (bool) : If True, overwrite existing data in SDS archive.

        Returns: None. Instead an SDS volume is created/expanded.

    '''

    secsPerDay = 86400  
    while startt<endt:
        print(startt)
        eod = startt+secsPerDay 
        # read from SDS - if no data download from FDSN

        thisSDSobj = SDS.SDSobj(SDS_TOP) 
        
        if thisSDSobj.read(startt, eod, speed=2) or overwrite: # non-zero return value means no data in SDS so we will use FDSN
            # read from FDSN
            if not trace_ids:
                if inv: 
                    trace_ids = InventoryTools.inventory2traceid(inv)
                else:
                    inv = FDSNtools.get_inventory(fdsnURL, startt, eod, centerlat, centerlon, \
                                                        searchRadiusDeg, overwrite=overwrite ) # could add N S L C requirements too
                    if inv:
                        trace_ids = InventoryTools.inventory2traceid(inv)
            if trace_ids:
                st = FDSNtools.get_stream(fdsnURL, trace_ids, startt, eod, overwrite=overwrite)
                thisSDSobj.stream = st
                thisSDSobj.write(overwrite=overwrite) # save raw data to SDS
            else:
                print('SDS archive not written to.')

    

        startt+=secsPerDay # add 1 day 



def SDS_to_RSAM_wrapper(startt, endt, SDS_TOP, freqmin=0.5, freqmax=15.0, \
        zerophase=False, corners=2, sampling_interval=60.0, sourcelat=None, \
            sourcelon=None, inv=None, trace_ids=None, overwrite=True, verbose=False):
    '''
    Load Stream from SDS archive and create RSAM metrics. RSAM by default is the mean absolute value in each 60-s window.
    
    Raw RSAM (counts) is generated by default. If inv name-value parameter given, an instrument corrected RSAM (m/s) will be generated.
    If sourcelat and sourcelon name-value parameters given, surface-wave reduced displacement (cm^2) will be generated.

        Parameters:
            startt (UTCDateTime): An ObsPy UTCDateTime marking the start date/time of the data request.
            endt (UTCDateTime)  : An ObsPy UTCDateTime marking the end date/time of the data request.
            SDS_TOP (str)       : The path to the SDS directory structure.

        Optional Name-Value Parameters:
            trace_ids (List)    : A list of N.S.L.C strings. Default None. If given, only these trace ids will be read from SDS archive.
            inv (Inventory)     : An ObsPy Inventory object. Default None. 
            sourcelat (float)   : Decimal degrees latitude for assumed seismic point source. Default None.
            sourcelon (float)   : Decimal degrees longitude for assumed seismic point source. Default None.
            freqmin (float) : Bandpass minimum. Default 0.5 Hz.
            freqmax (float) : Bandpass maximum. Default 15.0 Hz.
            zerophase (bool) : If True, a two-way pass, acausal, zero-phase bandpass filter is applied to the data. Default False, which is a causal one-way filter.
            corners (int) : Filter is applied this many times. Default 2.
            sampling_interval (float) : bin size (in seconds) for binning data to compute RSAM.
            overwrite (bool) : If True, overwrite existing data in RSAM archive.

        Returns: None. Instead an RSAM volume (a variant of an SDS volume) is created/expanded.

    '''   

    secsPerDay = 86400  
    while startt<endt:
        print(startt)
        eod = startt+secsPerDay #-1/10000
        # read from SDS - if no data download from FDSN

        thisSDSobj = SDS.SDSobj(SDS_TOP) 
        if not thisSDSobj.read(startt-3600, eod+3600, speed=2, trace_ids=trace_ids) or overwrite: # non-zero return value means no data in SDS so we will use FDSN

            # compute instrument-corrected RSAM
            thisRSAMobj = RSAMobj(st=thisSDSobj.stream.copy(), inv=inv, sampling_interval=sampling_interval, \
                              freqmin=freqmin, zerophase=zerophase, corners=corners, verbose=verbose, startt=startt, endt=eod)
            thisRSAMobj.write(SDS_TOP) # write RSAM to an SDS-like structure
        
            # compute/write reduced displacement
            if sourcelat and sourcelon and inv:
                thisDRSobj = ReducedDisplacementObj(st=thisSDSobj.stream.copy(), inv=inv, sampling_interval=sampling_interval, \
                                freqmin=freqmin, freqmax=freqmax, zerophase=zerophase, corners=corners, \
                                     sourcelat=sourcelat, sourcelon=sourcelon, verbose=verbose, startt=startt, endt=eod )
                thisDRSobj.write(SDS_TOP) # write Drs to an SDS-like structure
    

        startt+=secsPerDay # add 1 day 


def SDS_to_spectrogram_wrapper(startt, endt, SDS_TOP, trace_ids, windowlength=600, overwrite=False, equal_scale=True, dbscale=True, clim=None, inv=None, verbose=False):
    '''
    Load Stream from SDS archive and create RSAM metrics. RSAM by default is the mean absolute value in each 60-s window.
    
    Raw RSAM (counts) is generated by default. If inv name-value parameter given, an instrument corrected RSAM (m/s) will be generated.
    If sourcelat and sourcelon name-value parameters given, surface-wave reduced displacement (cm^2) will be generated.

        Parameters:
            startt (UTCDateTime): An ObsPy UTCDateTime marking the start date/time of the data request.
            endt (UTCDateTime)  : An ObsPy UTCDateTime marking the end date/time of the data request.
            SDS_TOP (str)       : The path to the SDS directory structure.

        Optional Name-Value Parameters:
            trace_ids (List)    : A list of N.S.L.C strings. Default None. If given, only these trace ids will be read from SDS archive.
            inv (Inventory)     : An ObsPy Inventory object. Default None. 
            sourcelat (float)   : Decimal degrees latitude for assumed seismic point source. Default None.
            sourcelon (float)   : Decimal degrees longitude for assumed seismic point source. Default None.
            freqmin (float) : Bandpass minimum. Default 0.5 Hz.
            freqmax (float) : Bandpass maximum. Default 15.0 Hz.
            zerophase (bool) : If True, a two-way pass, acausal, zero-phase bandpass filter is applied to the data. Default False, which is a causal one-way filter.
            corners (int) : Filter is applied this many times. Default 2.
            sampling_interval (float) : bin size (in seconds) for binning data to compute RSAM.
            overwrite (bool) : If True, overwrite existing data in RSAM archive.

        Returns: None. Instead an RSAM volume (a variant of an SDS volume) is created/expanded.

    '''   
    sotw = startt
    freqmin=0.2
    freqmax=25.0
    while sotw<endt:
        print(sotw)
        eotw = sotw+windowlength #-1/10000
        # read from SDS - if no data download from FDSN

        thisSDSobj = SDS.SDSobj(SDS_TOP) 
        
        
        if inv:
            thisSDSobj.read(sotw-windowlength/2, eotw+windowlength/2, speed=2, trace_ids=trace_ids)
            st = thisSDSobj.stream
            pre_filt = [freqmin/1.2, freqmin, freqmax, freqmax*1.2]
            for tr in st:
                if tr.stats.channel[2] in 'ENZ' : # filter seismic channels only
                    print('Processing %s' % tr.id)
                    tr.remove_response(output='DISP', inventory=inv, plot=verbose, pre_filt=pre_filt, water_level=60)    
            st.trim(starttime=sotw, endtime=eotw)
        else:
            thisSDSobj.read(sotw, eotw, speed=2, trace_ids=trace_ids)
            st = thisSDSobj.stream

        spobj = IceWeb.icewebSpectrogram(stream=st)
        sgramfile = '%s.%s.png' % (st[0].stats.network, sotw.strftime('%Y%m%dT%H%M%S'))
        if not os.path.isfile(sgramfile) or overwrite:
            print(sgramfile)
            spobj.plot(outfile=sgramfile, dbscale=dbscale, title=sgramfile, equal_scale=equal_scale, clim=clim, fmin=freqmin, fmax=freqmax)

        sotw+=windowlength

def order_traces_by_distance(st, r=[], assert_channel_order=False): 
    st2 = Stream()
    if not r:
        r = [tr.stats.distance for tr in st]
    if assert_channel_order: # modifies r to order channels by (HH)ZNE and then HD(F123) etc.
        for i, tr in enumerate(st):
            c1 = int(tr.stats.location)/1000000
            numbers = 'ZNEF0123456789'
            c2 = numbers.find(tr.stats.channel[2])/1000000000
            r[i] += c1 + c2
    indices = np.argsort(r)
    for i in indices:
        tr = st[i].copy()
        st2.append(tr)

    return st2


def SDS_to_ICEWEB_wrapper(startt, endt, SDS_TOP, freqmin=0.5, freqmax=15.0, \
        zerophase=False, corners=2, sampling_interval=60.0, sourcelat=None, \
            sourcelon=None, inv=None, trace_ids=None, overwrite=True, verbose=False, sgrammins=10,  \
                equal_scale=True, dbscale=True, clim=[1e-8, 1e-5], subnet=None, SGRAM_TOP='.'):
    '''
    Load Stream from SDS archive and create RSAM metrics. RSAM by default is the mean absolute value in each 60-s window.
    
    Raw RSAM (counts) is generated by default. If inv name-value parameter given, an instrument corrected RSAM (m/s) will be generated.
    If sourcelat and sourcelon name-value parameters given, surface-wave reduced displacement (cm^2) will be generated.

        Parameters:
            startt (UTCDateTime): An ObsPy UTCDateTime marking the start date/time of the data request.
            endt (UTCDateTime)  : An ObsPy UTCDateTime marking the end date/time of the data request.
            SDS_TOP (str)       : The path to the SDS directory structure.

        Optional Name-Value Parameters:
            trace_ids (List)    : A list of N.S.L.C strings. Default None. If given, only these trace ids will be read from SDS archive.
            inv (Inventory)     : An ObsPy Inventory object. Default None. 
            sourcelat (float)   : Decimal degrees latitude for assumed seismic point source. Default None.
            sourcelon (float)   : Decimal degrees longitude for assumed seismic point source. Default None.
            freqmin (float) : Bandpass minimum. Default 0.5 Hz.
            freqmax (float) : Bandpass maximum. Default 15.0 Hz.
            zerophase (bool) : If True, a two-way pass, acausal, zero-phase bandpass filter is applied to the data. Default False, which is a causal one-way filter.
            corners (int) : Filter is applied this many times. Default 2.
            sampling_interval (float) : bin size (in seconds) for binning data to compute RSAM.
            overwrite (bool) : If True, overwrite existing data in RSAM archive.
            verbose (bool) : If True, additional output is genereated for troubleshooting.

        Returns: None. Instead an RSAM volume (a variant of an SDS volume) is created/expanded.

    '''   


    secsPerDay = 86400  
    taperSecs = 3600 # extra data to load for response removal tapering
    sod = startt
    while sod<endt:
        f"Processing {sod}"
        eod = sod+secsPerDay #-1/10000
        # read from SDS
        thisSDSobj = SDS.SDSobj(SDS_TOP) 
        
        if inv: # with inventory CSAM, Drs, and spectrograms

            thisSDSobj.read(sod-taperSecs, eod+taperSecs, speed=2, trace_ids=trace_ids)
            st = thisSDSobj.stream

            InventoryTools.attach_station_coordinates_from_inventory(inv, st)
            InventoryTools.attach_distance_to_stream(st, sourcelat, sourcelon) 
            r = [tr.stats.distance for tr in st]
            if verbose:
                f"SDS Stream: {st}"
                f"Distances: {r}"
            st = order_traces_by_distance(st, r, assert_channel_order=True)
            print(st, [tr.stats.distance for tr in st])
            #VEL = order_traces_by_distance(VEL, r, assert_channel_order=True)

            pre_filt = [freqmin/1.2, freqmin, freqmax, freqmax*1.2]
            if verbose:
                f"Correcting to velocity seismogram"
            VEL = st.copy().select(channel="*H*").remove_response(output='VEL', inventory=inv, plot=verbose, pre_filt=pre_filt, water_level=60)
            if verbose:
                f"Correcting to displacement seismogram"
            DISP = st.copy().select(channel="*H*").remove_response(output='DISP', inventory=inv, plot=verbose, pre_filt=pre_filt, water_level=60)
            if verbose:
                f"Trimming to 24-hour day from {sod} to {eod}"
            VEL.trim(starttime=sod, endtime=eod)
            DISP.trim(starttime=sod, endtime=eod)

            # compute instrument-corrected RSAM
            if verbose:
                f"Computing corrected RSAM"
            thisRSAMobj = IceWeb.RSAMobj(st=VEL, inv=inv, sampling_interval=sampling_interval, freqmin=freqmin, freqmax=freqmax, \
                               zerophase=zerophase, corners=corners, verbose=verbose, startt=sod, endt=eod, units='m/s', absolute=True)
            if verbose:
                f"Saving corrected RSAM to SDS"
            thisRSAMobj.write(SDS_TOP) # write RSAM to an SDS-like structure

            # compute/write reduced displacement
            if sourcelat and sourcelon:
                if verbose:
                    f"Computing DRS"
                thisDRSobj = IceWeb.ReducedDisplacementObj(st=DISP, inv=inv, sampling_interval=sampling_interval, \
                                freqmin=freqmin, freqmax=freqmax, zerophase=zerophase, corners=corners, \
                                     sourcelat=sourcelat, sourcelon=sourcelon, verbose=verbose, units='m' )
                if verbose:
                    f"Writing DRS to SDS"
                thisDRSobj.write(SDS_TOP) # write Drs to an SDS-like structure

            # spectrograms
            sotw = sod
            while sotw<eod:
                eotw = sotw + sgrammins * 60
                if verbose:
                    f"Generating spectrogram from {sotw} to {eotw}"
                tw_st = VEL.copy().trim(starttime=sotw, endtime=eotw)
                if isinstance(tw_st, Stream) and len(tw_st)>0 and tw_st[0].stats.npts>1000:
                    pass
                else:
                    if verbose:
                        f"- Not possible"
                    sotw += sgrammins * 60    
                    continue
                sgramdir = os.path.join(SGRAM_TOP, tw_st[0].stats.network, sotw.strftime('%Y'), sotw.strftime('%j'))
                sgrambase = '%s_%s.png' % (subnet, sotw.strftime('%Y%m%d-%H%M'))
                sgramfile = os.path.join(sgramdir, sgrambase)
                if not os.path.isdir(sgramdir):
                    os.makedirs(sgramdir)
                if not os.path.isfile(sgramfile) or overwrite:
                    print(sgramfile)
                    spobj = IceWeb.icewebSpectrogram(stream=tw_st)
                    fh, ah = spobj.plot(outfile=sgramfile, dbscale=dbscale, title=sgramfile, equal_scale=equal_scale, clim=clim, fmin=freqmin, fmax=freqmax)
                    try:
                        fh.close()
                    except:
                        plt.close()

                sotw += sgrammins * 60    

        else: # No inventory, just raw RSAM
            thisSDSobj.read(sotw, eotw, speed=2, trace_ids=trace_ids)
            if verbose:
                f"SDS Stream: {thisSDSob.stream}"
                f"Computing raw RSAM"
            thisRSAMobj = IceWeb.RSAMobj(st=thisSDSobj.stream, sampling_interval=sampling_interval, freqmin=freqmin, freqmax=freqmax, \
                               zerophase=zerophase, corners=corners, verbose=verbose, startt=startt, endt=eod, units='Counts', absolute=True)
            if verbose:
                f"Saving raw RSAM to SDS"
            thisRSAMobj.write(SDS_TOP) # write RSAM to an SDS-like structure


      
    

        sod+=secsPerDay # add 1 day 
        
