# Open and Distributed Data Monitoring

## Dependencies

        - if python < 2.5, then we need `argparse` package
        - pyzmq 

## Build binary rpm package

    python setup.py bdist_rpm

## Metric plugins

There are a few requirement for a valid plugin extension:

- A plugin needs to be named starting with `metric_`. 

- A plugin needs to implement three required method:
    
    - `metric_init()`
    - `metric_cleanup()`
    - `get_stats()`

This is similar to Ganglia. Since we forgo all the metadata attributes Ganglia
plugin has to supply. There are limitation or requirements on what kind of
data a metric collector can return:

In short, we expect a dictionary:

    {   target 1: {
                        { key : value }, 
                        { key : value }
                        ...
                  }
        target 2: { 
                        { key : value },
                        { key : value },
                        ...
                  }
        ...
    }

## Data Archiving

TBD
