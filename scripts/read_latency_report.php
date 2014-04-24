<?php
function graph_read_latency_report ( &$rrdtool_graph ) {

################# CHANGE THESE #################
$color = '#0000FF';
$metric = 'ycsb_READ';
$title = 'Read Latency';
$vertical_label = 'latency (ms)';

################################################
    global $conf,
           $context,
           $range,
           $rrd_dir,
           $size;

    if ($conf['strip_domainname']) {
       $hostname = strip_domainname($GLOBALS['hostname']);
    } else {
       $hostname = $GLOBALS['hostname'];
    }

    // variables otherwise, the graph *will not work*.
    //
    if ($context != 'host') {
       //  This will be turned into: "Clustername $TITLE last $timerange",
       //  so keep it short
       $rrdtool_graph['title']  = $title;
    } else {
       $rrdtool_graph['title']  = "$hostname $title last $range";
    }
    $rrdtool_graph['vertical-label'] = $vertical_label;
    // Fudge to account for number of lines in the chart legend
    $rrdtool_graph['height']        += ($size == 'medium') ? 28 : 0;
    $rrdtool_graph['upper-limit']    = '100';
    $rrdtool_graph['lower-limit']    = '0';
    $rrdtool_graph['extras']         = '--rigid';

    /*
     * Here we actually build the chart series.  This is moderately complicated
     * to show off what you can do.  For a simpler example, look at
     * network_report.php
     */
    if($context != "host" ) {

        /*
         * If we are not in a host context, then we need to calculate
         * the average
         */
        $series =
              "'DEF:num_nodes=${rrd_dir}/$metric.rrd:num:AVERAGE' "
            . "'DEF:metric=${rrd_dir}/$metric.rrd:sum:AVERAGE' "
            . "'CDEF:cumulative=metric,num_nodes,/' "
            . "'LINE:cumulative$color:$metric' ";



    } 


    // We have everything now, so add it to the array, and go on our way.
    $rrdtool_graph['series'] = $series;

    return $rrdtool_graph;
}

?>
